# -*- coding: utf-8 -*-
import asyncio
import os
import queue
import random
import struct
import threading
import time
import traceback
import winsound

import addonHandler
import wx
import ui
from logHandler import log

from .core.gemini_imports import (
	GENAI_AVAILABLE,
	GENAI_IMPORT_ERROR,
	PYAUDIO_AVAILABLE,
	PYAUDIO_IMPORT_ERROR,
	VENDOR_VERSIONS,
	genai,
	getRuntimeScope,
	pyaudio,
	types,
)

addonHandler.initTranslation()


MODEL_NAME = "gemini-3.1-flash-live-preview"
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
STREAM_START_SOUND_PATH = os.path.join(MEDIA_DIR, "stream-start.wav")
STREAM_END_SOUND_PATH = os.path.join(MEDIA_DIR, "stream-end.wav")

FORMAT = pyaudio.paInt16 if pyaudio else 8
CHANNELS = 1
INPUT_RATE = 16000
OUTPUT_RATE = 24000
CHUNK = 1024
BUFFER_THRESHOLD = 5
MIN_BUFFER_THRESHOLD = 2
MAX_BUFFER_THRESHOLD = 10
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 20.0
BACKOFF_JITTER_SECONDS = 0.4
HISTORY_MAX_TURNS = 12
HISTORY_MAX_CHARS = 1800


class TalkWithAIRuntimeError(RuntimeError):
	pass


class TalkWithAIDialog(wx.Dialog):
	def __init__(self, parent, apiKey, voiceName, systemInstruction):
		# Translators: Title of the dialog for the "Talk With AI" feature (REAL-TIME conversation).
		super().__init__(parent, title=_("Talk With AI"), size=(420, 320))
		self.apiKey = apiKey
		self.voiceName = voiceName
		self.systemInstruction = systemInstruction

		self.client = None
		self.session = None
		self.sessionActive = False
		self.loop = None
		self.loopThread = None
		self.audioInterface = None
		self.inputStream = None
		self.outputStream = None
		self.micOn = True
		self.useGoogleSearch = False
		self.selectedThinkingLevel = "minimal"
		self.historyConfigSupported = True

		self.audioQueue = queue.Queue()
		self.isPlaying = False
		self.volume = 80
		self.bufferThreshold = BUFFER_THRESHOLD
		self.lastBufferAdjustAt = 0.0
		self.lastStatusAt = 0.0
		self.lastAnnouncedStatus = ""
		self._isClosing = False
		self.sessionHistory = []
		self.historyLock = threading.Lock()

		self.inputDevices = self._getDeviceList(input=True)
		self.outputDevices = self._getDeviceList(input=False)
		self.selectedInputIdx = None
		self.selectedOutputIdx = None
		self.thinkingChoices = [
			# Translators: Choice label for the lowest reasoning setting in Talk With AI.
			(_("No Thinking"), "minimal"),
			# Translators: Choice label for low reasoning depth in Talk With AI.
			(_("Low"), "low"),
			# Translators: Choice label for medium reasoning depth in Talk With AI.
			(_("Medium"), "medium"),
			# Translators: Choice label for high reasoning depth in Talk With AI.
			(_("High"), "high"),
		]

		self._buildUi()
		self.compatibilityError = self._getRuntimeCompatibilityError()

		if not PYAUDIO_AVAILABLE:
			wx.CallAfter(
				self.reportError,
				self._buildMissingDependencyMessage(
					_("PyAudio is not available. This feature requires a working PyAudio installation."),
					PYAUDIO_IMPORT_ERROR,
				),
			)
			self.connectBtn.Disable()
		if not GENAI_AVAILABLE:
			wx.CallAfter(
				self.reportError,
				self._buildMissingDependencyMessage(
					_("Google GenAI is not available."),
					GENAI_IMPORT_ERROR,
				),
			)
			self.connectBtn.Disable()
		elif self.compatibilityError:
			wx.CallAfter(self.reportError, self.compatibilityError)
			self.connectBtn.Disable()

		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

	def _logCleanupFailure(self, action, error):
		log.debug(f"Talk With AI cleanup issue during {action}: {error}", exc_info=True)

	def _getDeviceList(self, input=True):
		"""Returns a list of dicts: {'index': int, 'name': str}"""
		devices = []
		if not PYAUDIO_AVAILABLE:
			return devices
		with getRuntimeScope():
			p = pyaudio.PyAudio()
		try:
			info = p.get_host_api_info_by_index(0)
			numDevices = info.get("deviceCount")
			for i in range(numDevices):
				dev = p.get_device_info_by_host_api_device_index(0, i)
				if input:
					if int(dev.get("maxInputChannels", 0)) > 0:
						devices.append({"index": i, "name": dev.get("name")})
				else:
					if int(dev.get("maxOutputChannels", 0)) > 0:
						devices.append({"index": i, "name": dev.get("name")})
		except Exception as error:
			log.error(f"Error listing devices: {error}")
		finally:
			p.terminate()
		return devices

	def _buildUi(self):
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		panel = wx.Panel(self)
		panelSizer = wx.BoxSizer(wx.VERTICAL)

		statusBox = wx.StaticBox(panel, label=_("Status"))
		statusSizer = wx.StaticBoxSizer(statusBox, wx.VERTICAL)
		self.statusLabel = wx.StaticText(
			panel,
			label=_("Status: {status}").format(status=_("Ready to Connect")),
		)
		statusSizer.Add(self.statusLabel, 0, wx.ALL | wx.EXPAND, 5)
		panelSizer.Add(statusSizer, 0, wx.ALL | wx.EXPAND, 5)

		controlsBox = wx.StaticBox(panel, label=_("Controls"))
		controlsSizer = wx.StaticBoxSizer(controlsBox, wx.VERTICAL)

		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Button to start the voice conversation.
		self.connectBtn = wx.Button(panel, label=_("Start Conversation"))
		self.connectBtn.Bind(wx.EVT_BUTTON, self.onConnect)
		# Translators: Button to stop the voice conversation.
		self.disconnectBtn = wx.Button(panel, label=_("Stop Conversation"))
		self.disconnectBtn.Bind(wx.EVT_BUTTON, self.onDisconnect)
		self.disconnectBtn.Disable()

		btnSizer.Add(self.connectBtn, 1, wx.RIGHT, 5)
		btnSizer.Add(self.disconnectBtn, 1, wx.LEFT, 5)
		controlsSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, 5)

		# Translators: Toggle button label indicating microphone is ON.
		self.micBtn = wx.ToggleButton(panel, label=_("Microphone: ON"))
		self.micBtn.SetValue(True)
		self.micBtn.Bind(wx.EVT_TOGGLEBUTTON, self.onMicToggle)
		controlsSizer.Add(self.micBtn, 0, wx.ALL | wx.EXPAND, 5)

		self.deviceSizer = wx.BoxSizer(wx.VERTICAL)

		inputSizer = wx.BoxSizer(wx.HORIZONTAL)
		inputLabel = wx.StaticText(panel, label=_("Microphone:"))
		inputChoices = [device["name"] for device in self.inputDevices]
		self.inputChoice = wx.Choice(panel, choices=inputChoices)
		if inputChoices:
			self.inputChoice.SetSelection(0)
		inputSizer.Add(inputLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		inputSizer.Add(self.inputChoice, 1, wx.EXPAND)
		self.deviceSizer.Add(inputSizer, 0, wx.ALL | wx.EXPAND, 5)

		outputSizer = wx.BoxSizer(wx.HORIZONTAL)
		outputLabel = wx.StaticText(panel, label=_("Speaker:"))
		outputChoices = [device["name"] for device in self.outputDevices]
		self.outputChoice = wx.Choice(panel, choices=outputChoices)
		if outputChoices:
			self.outputChoice.SetSelection(0)
		outputSizer.Add(outputLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		outputSizer.Add(self.outputChoice, 1, wx.EXPAND)
		self.deviceSizer.Add(outputSizer, 0, wx.ALL | wx.EXPAND, 5)

		controlsSizer.Add(self.deviceSizer, 0, wx.EXPAND)

		# Translators: Checkbox to enable grounding with Google Search in Talk With AI.
		self.googleSearchCb = wx.CheckBox(panel, label=_("Grounding with Google Search"))
		self.googleSearchCb.SetValue(False)
		controlsSizer.Add(self.googleSearchCb, 0, wx.ALL | wx.EXPAND, 5)

		thinkingSizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for choosing the reasoning depth in Talk With AI.
		self.thinkingLabel = wx.StaticText(panel, label=_("Thinking level:"))
		self.thinkingChoice = wx.Choice(panel, choices=[label for label, _value in self.thinkingChoices])
		self.thinkingChoice.SetSelection(0)
		thinkingSizer.Add(self.thinkingLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		thinkingSizer.Add(self.thinkingChoice, 1, wx.EXPAND)
		controlsSizer.Add(thinkingSizer, 0, wx.ALL | wx.EXPAND, 5)

		volSizer = wx.BoxSizer(wx.HORIZONTAL)
		volLabel = wx.StaticText(panel, label=_("Volume:"))
		self.volSlider = wx.Slider(panel, value=self.volume, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
		self.volSlider.Bind(wx.EVT_SLIDER, self.onVolumeChange)
		volSizer.Add(volLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		volSizer.Add(self.volSlider, 1, wx.EXPAND)
		controlsSizer.Add(volSizer, 0, wx.ALL | wx.EXPAND, 5)

		panelSizer.Add(controlsSizer, 0, wx.ALL | wx.EXPAND, 5)

		infoLabel = wx.StaticText(
			panel,
			label=_("Voice: {voiceName}").format(voiceName=str(self.voiceName)),
		)
		panelSizer.Add(infoLabel, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

		panel.SetSizer(panelSizer)
		mainSizer.Add(panel, 1, wx.EXPAND)
		self.SetSizer(mainSizer)
		self.CenterOnParent()

	def _announceStatus(self, text, force=False):
		message = str(text or "").strip()
		if not message:
			return
		if not force and message == self.lastAnnouncedStatus:
			return
		self.lastAnnouncedStatus = message
		try:
			ui.message(message)
		except Exception as error:
			self._logCleanupFailure("status announcement", error)

	def updateStatus(self, text, announce=False, forceAnnouncement=False):
		try:
			if self:
				self.statusLabel.SetLabel(_("Status: {status}").format(status=text))
		except RuntimeError:
			return
		if announce:
			self._announceStatus(text, force=forceAnnouncement)

	def reportError(self, msg):
		try:
			if self:
				wx.MessageBox(str(msg), _("Error"), wx.OK | wx.ICON_ERROR)
				self.updateStatus(_("Error"))
		except RuntimeError:
			return

	def onMicToggle(self, evt):
		self.micOn = self.micBtn.GetValue()
		label = _("Microphone: ON") if self.micOn else _("Microphone: OFF")
		self.micBtn.SetLabel(label)

	def onVolumeChange(self, evt):
		self.volume = self.volSlider.GetValue()

	def _getSelectedThinkingLevel(self):
		selection = self.thinkingChoice.GetSelection()
		if selection == wx.NOT_FOUND:
			return "minimal"
		return self.thinkingChoices[selection][1]

	def _clearSessionHistory(self):
		with self.historyLock:
			self.sessionHistory = []

	def _buildMissingDependencyMessage(self, baseMessage, errorDetail):
		if not errorDetail:
			return baseMessage
		return _("{baseMessage}\n\nImport detail: {errorDetail}").format(
			baseMessage=baseMessage,
			errorDetail=errorDetail,
		)

	def _mergeHistoryText(self, existing, incoming):
		if not existing:
			return incoming
		if incoming == existing or existing.endswith(incoming):
			return existing
		if incoming.startswith(existing):
			return incoming
		if existing.startswith(incoming):
			return existing
		return f"{existing} {incoming}"

	def _rememberConversationTurn(self, role, text):
		cleaned = str(text or "").strip()
		if not cleaned:
			return
		with self.historyLock:
			if self.sessionHistory and self.sessionHistory[-1]["role"] == role:
				self.sessionHistory[-1]["text"] = self._mergeHistoryText(
					self.sessionHistory[-1]["text"],
					cleaned,
				)
			else:
				self.sessionHistory.append({"role": role, "text": cleaned})
			self._trimSessionHistory()

	def _trimSessionHistory(self):
		if len(self.sessionHistory) > HISTORY_MAX_TURNS:
			self.sessionHistory = self.sessionHistory[-HISTORY_MAX_TURNS:]
		totalChars = sum(len(turn["text"]) for turn in self.sessionHistory)
		while self.sessionHistory and totalChars > HISTORY_MAX_CHARS:
			totalChars -= len(self.sessionHistory.pop(0)["text"])

	def _buildReconnectHistoryTurns(self):
		with self.historyLock:
			return [
				types.Content(
					role=turn["role"],
					parts=[types.Part(text=turn["text"])],
				)
				for turn in self.sessionHistory
				if turn["text"].strip()
			]

	def _buildSystemInstruction(self):
		baseRules = (
			"You are a voice assistant for blind and low-vision users. "
			"Never fabricate facts. If uncertain, explicitly say you are not sure."
		)
		userInstruction = self.systemInstruction.strip() if self.systemInstruction else ""
		parts = [baseRules]
		if userInstruction:
			parts.append(f"User preference:\n{userInstruction}")
		return "\n\n".join(parts)

	def _buildReconnectDelay(self, attempt):
		baseDelay = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1)))
		return baseDelay + random.uniform(0.0, BACKOFF_JITTER_SECONDS)

	def _getRuntimeCompatibilityError(self):
		if not GENAI_AVAILABLE:
			return None
		requiredTypeNames = (
			"LiveConnectConfig",
			"SpeechConfig",
			"VoiceConfig",
			"PrebuiltVoiceConfig",
			"ThinkingConfig",
			"AudioTranscriptionConfig",
			"Blob",
			"HistoryConfig",
			"Content",
			"Part",
			"Tool",
			"GoogleSearch",
		)
		missing = [name for name in requiredTypeNames if not hasattr(types, name)]
		if not hasattr(genai, "Client"):
			missing.append("Client")
		if missing:
			version = VENDOR_VERSIONS.get("google.genai", "")
			if version:
				return _(
					"Installed google-genai library ({version}) does not support the Gemini 3.1 Live API features required by Talk With AI. Missing: {missing}. Please update the add-on libraries.",
				).format(
					version=version,
					missing=", ".join(missing),
				)
			return _(
				"Installed google-genai library does not support the Gemini 3.1 Live API features required by Talk With AI. Missing: {missing}. Please update the add-on libraries.",
			).format(
				missing=", ".join(missing),
			)
		return None

	def onConnect(self, evt):
		if self.compatibilityError:
			self.reportError(self.compatibilityError)
			return

		self.connectBtn.Disable()
		self.disconnectBtn.Enable()

		self.useGoogleSearch = self.googleSearchCb.GetValue()
		self.selectedThinkingLevel = self._getSelectedThinkingLevel()

		self.googleSearchCb.Hide()
		self.thinkingLabel.Hide()
		self.thinkingChoice.Hide()

		inSel = self.inputChoice.GetSelection()
		if inSel != wx.NOT_FOUND and self.inputDevices:
			self.selectedInputIdx = self.inputDevices[inSel]["index"]

		outSel = self.outputChoice.GetSelection()
		if outSel != wx.NOT_FOUND and self.outputDevices:
			self.selectedOutputIdx = self.outputDevices[outSel]["index"]

		for child in self.deviceSizer.GetChildren():
			window = child.GetWindow()
			if window:
				window.Hide()
			sizer = child.GetSizer()
			if sizer:
				for nestedChild in sizer.GetChildren():
					nestedWindow = nestedChild.GetWindow()
					if nestedWindow:
						nestedWindow.Hide()

		self.Layout()
		self.updateStatus(_("Connecting..."), announce=True)

		self.sessionActive = True
		self.loopThread = threading.Thread(target=self._startAsyncLoop, daemon=True)
		self.loopThread.start()

	def onDisconnect(self, evt):
		self.disconnectBtn.Disable()
		self.updateStatus(_("Disconnecting..."), announce=True)
		if self.loop and self.loop.is_running():
			asyncio.run_coroutine_threadsafe(self.cleanupAsync(), self.loop)

	def _playSoundEffect(self, path):
		def _bgPlay():
			try:
				if os.path.exists(path):
					winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
			except Exception as error:
				self._logCleanupFailure("sound effect playback", error)

		threading.Thread(target=_bgPlay, daemon=True).start()

	def onCharHook(self, evt):
		if evt.GetKeyCode() == wx.WXK_ESCAPE:
			self.Close()
		else:
			evt.Skip()

	def onClose(self, evt):
		self._isClosing = True
		self.sessionActive = False
		self.isPlaying = False
		self._clearSessionHistory()
		self._flushAudioQueue()
		self.audioQueue.put(b"")

		if self.loop and self.loop.is_running():
			try:
				asyncio.run_coroutine_threadsafe(self._shutdownLoop(), self.loop)
			except Exception as error:
				self._logCleanupFailure("loop shutdown scheduling", error)
		elif self.audioInterface:
			try:
				self.audioInterface.terminate()
			except Exception as error:
				self._logCleanupFailure("audio interface termination", error)

		self.Destroy()

	async def _shutdownLoop(self):
		try:
			await self.cleanupAsync()
		finally:
			loop = asyncio.get_running_loop()
			loop.stop()

	def _startAsyncLoop(self):
		try:
			self.loop = asyncio.new_event_loop()
			asyncio.set_event_loop(self.loop)
			self.loop.run_until_complete(self.runSession())
		except RuntimeError as error:
			self._logCleanupFailure("async loop shutdown", error)
		except Exception as error:
			log.error(f"Async Loop Error: {error}", exc_info=True)
		finally:
			try:
				pending = asyncio.all_tasks(self.loop)
				for task in pending:
					task.cancel()
				if pending and not self.loop.is_closed():
					self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
				if not self.loop.is_closed():
					self.loop.close()
			except Exception as error:
				self._logCleanupFailure("async loop finalization", error)

	def _flushAudioQueue(self):
		while not self.audioQueue.empty():
			try:
				self.audioQueue.get_nowait()
			except queue.Empty:
				break

	async def cleanupAsync(self):
		self.sessionActive = False
		self.isPlaying = False
		self.session = None

		currentTask = asyncio.current_task()
		for task in asyncio.all_tasks():
			if task is not currentTask:
				task.cancel()

		self._flushAudioQueue()

		if self.inputStream:
			self.inputStream.stop_stream()
			self.inputStream.close()
			self.inputStream = None
		if self.outputStream:
			self.outputStream.stop_stream()
			self.outputStream.close()
			self.outputStream = None
		if self.audioInterface:
			self.audioInterface.terminate()
			self.audioInterface = None

	def _audioPlayerWorker(self):
		buffer = []
		buffering = True
		self.bufferThreshold = BUFFER_THRESHOLD

		while self.sessionActive and self.isPlaying:
			try:
				data = self.audioQueue.get(timeout=0.1)
				if self.volume != 100:
					count = len(data) // 2
					shorts = struct.unpack(f"{count}h", data)
					factor = self.volume / 100.0
					scaledShorts = []
					for sample in shorts:
						value = int(sample * factor)
						if value > 32767:
							value = 32767
						if value < -32768:
							value = -32768
						scaledShorts.append(value)
					data = struct.pack(f"{count}h", *scaledShorts)

				if buffering:
					buffer.append(data)
					if len(buffer) >= self.bufferThreshold:
						buffering = False
						if self.outputStream and self.outputStream.is_active():
							for chunk in buffer:
								self.outputStream.write(chunk)
						buffer = []
				else:
					if self.outputStream and self.outputStream.is_active():
						self.outputStream.write(data)
					queueDepth = self.audioQueue.qsize()
					now = time.monotonic()
					if queueDepth > self.bufferThreshold + 3 and self.bufferThreshold > MIN_BUFFER_THRESHOLD:
						if now - self.lastBufferAdjustAt > 1.0:
							self.bufferThreshold -= 1
							self.lastBufferAdjustAt = now
					elif queueDepth <= 1 and self.bufferThreshold < MAX_BUFFER_THRESHOLD:
						if now - self.lastBufferAdjustAt > 1.0:
							self.bufferThreshold += 1
							self.lastBufferAdjustAt = now
			except queue.Empty:
				if not buffering and self.sessionActive:
					buffering = True
					now = time.monotonic()
					if self.bufferThreshold < MAX_BUFFER_THRESHOLD and now - self.lastBufferAdjustAt > 0.8:
						self.bufferThreshold += 1
						self.lastBufferAdjustAt = now
				continue
			except Exception as error:
				log.error(f"Audio Player Error: {error}")
				break

	def _buildLiveConfig(self, includeHistorySeed):
		if not types:
			raise TalkWithAIRuntimeError(_("Google GenAI types are not available."))
		try:
			with getRuntimeScope():
				return types.LiveConnectConfig(
					response_modalities=["AUDIO"],
					speech_config=types.SpeechConfig(
						voice_config=types.VoiceConfig(
							prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voiceName),
						),
					),
					system_instruction=self._buildSystemInstruction(),
					thinking_config=types.ThinkingConfig(thinking_level=self.selectedThinkingLevel),
					input_audio_transcription=types.AudioTranscriptionConfig(),
					output_audio_transcription=types.AudioTranscriptionConfig(),
					tools=[types.Tool(google_search=types.GoogleSearch())] if self.useGoogleSearch else None,
					history_config=(
						types.HistoryConfig(initial_history_in_client_content=True)
						if includeHistorySeed and self.historyConfigSupported
						else None
					),
				)
		except Exception as error:
			raise TalkWithAIRuntimeError(
				_("Failed to prepare the Gemini Live configuration. Please update the add-on libraries."),
			) from error

	def _assertSessionCompatibility(self, session):
		for methodName in ("send_realtime_input", "send_client_content"):
			if not hasattr(session, methodName):
				version = VENDOR_VERSIONS.get("google.genai", "")
				if version:
					raise TalkWithAIRuntimeError(
						_(
							"The installed google-genai library ({version}) is too old for Gemini 3.1 Live sessions. Missing session method: {methodName}. Please update the add-on libraries.",
						).format(
							version=version,
							methodName=methodName,
						),
					)
				raise TalkWithAIRuntimeError(
					_(
						"The installed google-genai library is too old for Gemini 3.1 Live sessions. Missing session method: {methodName}. Please update the add-on libraries.",
					).format(
						methodName=methodName,
					),
				)

	async def _seedSessionHistory(self, session):
		historyTurns = self._buildReconnectHistoryTurns()
		if not historyTurns:
			return
		await session.send_client_content(turns=historyTurns, turn_complete=False)

	def _shouldRetryWithoutHistoryConfig(self, error, usedHistoryConfig):
		if not usedHistoryConfig or not self.historyConfigSupported:
			return False
		message = f"{error!r}".lower()
		return "history_config" in message or "initial_history_in_client_content" in message

	async def sendAudioLoop(self, session):
		while self.sessionActive:
			if self.micOn and self.inputStream and self.inputStream.is_active():
				try:
					data = await self.loop.run_in_executor(
						None,
						lambda: self.inputStream.read(CHUNK, exception_on_overflow=False),
					)
					with getRuntimeScope():
						audioBlob = types.Blob(data=data, mime_type=f"audio/pcm;rate={INPUT_RATE}")
					await session.send_realtime_input(audio=audioBlob)
				except asyncio.CancelledError:
					raise
				except Exception as error:
					log.error(f"Mic/Send Error: {error}")
					break
			else:
				await asyncio.sleep(0.1)

	def _queueAudioData(self, data):
		if data:
			self.audioQueue.put(data)

	def _handleServerContent(self, serverContent):
		queuedAudio = False
		if getattr(serverContent, "interrupted", False):
			log.debug("TalkWithAI: Server Interrupted")
			self._flushAudioQueue()
			return queuedAudio

		inputTranscription = getattr(serverContent, "input_transcription", None)
		if inputTranscription and getattr(inputTranscription, "text", None):
			self._rememberConversationTurn("user", inputTranscription.text)

		outputTranscription = getattr(serverContent, "output_transcription", None)
		if outputTranscription and getattr(outputTranscription, "text", None):
			self._rememberConversationTurn("model", outputTranscription.text)

		modelTurn = getattr(serverContent, "model_turn", None)
		if modelTurn is None:
			return queuedAudio
		for part in getattr(modelTurn, "parts", []) or []:
			inlineData = getattr(part, "inline_data", None)
			if inlineData is not None and getattr(inlineData, "data", None):
				self._queueAudioData(inlineData.data)
				queuedAudio = True
			textPart = getattr(part, "text", None)
			if textPart:
				self._rememberConversationTurn("model", textPart)
		return queuedAudio

	async def receiveLoop(self, session):
		try:
			async for response in session.receive():
				if not self.sessionActive:
					break

				text = getattr(response, "text", None)
				if text:
					self._rememberConversationTurn("model", text)

				serverContent = getattr(response, "server_content", None)
				queuedAudioFromServerContent = False
				if serverContent is not None:
					queuedAudioFromServerContent = self._handleServerContent(serverContent)

				data = getattr(response, "data", None)
				if data and not queuedAudioFromServerContent:
					# Current python-genai Live API examples consume audio from
					# server_content.model_turn.parts[].inline_data. Keep response.data
					# only as a fallback for compatibility with alternate payloads.
					self._queueAudioData(data)

				toolCall = getattr(response, "tool_call", None)
				if toolCall is not None:
					log.debug("TalkWithAI: Ignoring tool_call event from Live API.")
		except asyncio.CancelledError:
			raise
		except Exception as error:
			log.error(f"TalkWithAI Receive Loop Error: {error}")
		finally:
			log.debug("TalkWithAI: Receive loop ended")

	async def runSession(self):
		try:
			with getRuntimeScope():
				self.audioInterface = pyaudio.PyAudio()

			self.outputStream = self.audioInterface.open(
				format=FORMAT,
				channels=CHANNELS,
				rate=OUTPUT_RATE,
				output=True,
				frames_per_buffer=CHUNK,
				output_device_index=self.selectedOutputIdx,
			)

			self.inputStream = self.audioInterface.open(
				format=FORMAT,
				channels=CHANNELS,
				rate=INPUT_RATE,
				input=True,
				frames_per_buffer=CHUNK,
				input_device_index=self.selectedInputIdx,
			)

			with getRuntimeScope():
				self.client = genai.Client(api_key=self.apiKey, http_options={"api_version": "v1beta"})

			firstConnect = True
			retryAttempt = 0

			while self.sessionActive:
				usedHistoryConfig = False
				try:
					historyTurns = self._buildReconnectHistoryTurns()
					usedHistoryConfig = bool(historyTurns) and self.historyConfigSupported
					config = self._buildLiveConfig(includeHistorySeed=bool(historyTurns))

					log.debug("TalkWithAI: Connecting to Gemini Live 3.1...")
					with getRuntimeScope():
						async with self.client.aio.live.connect(model=MODEL_NAME, config=config) as session:
							self._assertSessionCompatibility(session)
							self.session = session

							if historyTurns:
								await self._seedSessionHistory(session)

							retryAttempt = 0
							if firstConnect:
								wx.CallAfter(self.updateStatus, _("Connected"), True)
								self._playSoundEffect(STREAM_START_SOUND_PATH)
								firstConnect = False
							else:
								log.debug("TalkWithAI: Reconnected silently")

							sendTask = asyncio.create_task(self.sendAudioLoop(session))
							receiveTask = asyncio.create_task(self.receiveLoop(session))

							if not self.isPlaying:
								playWorker = threading.Thread(target=self._audioPlayerWorker, daemon=True)
								self.isPlaying = True
								playWorker.start()

							_done, pending = await asyncio.wait(
								[sendTask, receiveTask],
								return_when=asyncio.FIRST_COMPLETED,
							)

							for task in pending:
								task.cancel()
								try:
									await task
								except asyncio.CancelledError:
									pass

				except TalkWithAIRuntimeError as error:
					log.error(f"TalkWithAI Compatibility Error: {error}")
					wx.CallAfter(self.reportError, str(error))
					self.sessionActive = False
				except asyncio.CancelledError:
					raise
				except Exception as error:
					if self._shouldRetryWithoutHistoryConfig(error, usedHistoryConfig):
						log.warning(
							"TalkWithAI: Live session rejected history_config; retrying without it.",
							exc_info=True,
						)
						self.historyConfigSupported = False
						continue
					log.error(f"TalkWithAI Session/Connection Error: {error}", exc_info=True)
					retryAttempt += 1
					delay = self._buildReconnectDelay(retryAttempt)
					now = time.monotonic()
					if now - self.lastStatusAt > 1.0:
						wx.CallAfter(
							self.updateStatus,
							_("Connection lost. Retrying in {seconds:.1f}s").format(seconds=delay),
							True,
						)
						self.lastStatusAt = now
					await asyncio.sleep(delay)

				if self.sessionActive:
					log.debug("TalkWithAI: Reconnecting...")

		except asyncio.CancelledError:
			pass
		except Exception:
			log.error(f"TalkWithAI Fatal Error: {traceback.format_exc()}")
			wx.CallAfter(self.reportError, traceback.format_exc())
			self.sessionActive = False
		finally:
			self._playSoundEffect(STREAM_END_SOUND_PATH)
			if not self._isClosing:
				wx.CallAfter(self.resetUi)
			if self.inputStream:
				self.inputStream.stop_stream()
				self.inputStream.close()
				self.inputStream = None
			if self.outputStream:
				self.outputStream.stop_stream()
				self.outputStream.close()
				self.outputStream = None
			if self.audioInterface:
				self.audioInterface.terminate()
				self.audioInterface = None
			self.session = None

	def resetUi(self):
		if self:
			try:
				self.connectBtn.Enable()
				self.disconnectBtn.Disable()
				self.googleSearchCb.Show()
				self.thinkingLabel.Show()
				self.thinkingChoice.Show()

				for child in self.deviceSizer.GetChildren():
					window = child.GetWindow()
					if window:
						window.Show()
					sizer = child.GetSizer()
					if sizer:
						for nestedChild in sizer.GetChildren():
							nestedWindow = nestedChild.GetWindow()
							if nestedWindow:
								nestedWindow.Show()

				self.Layout()
				self.updateStatus(_("Ready"), announce=True)
			except RuntimeError:
				pass
