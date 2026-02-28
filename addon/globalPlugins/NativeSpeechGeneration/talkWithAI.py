# -*- coding: utf-8 -*-
import wx
import threading
import asyncio
import traceback
import random
import time
from logHandler import log
import addonHandler

import os
import winsound
import queue

import struct

from .core.gemini_imports import (
	GENAI_AVAILABLE,
	PYAUDIO_AVAILABLE,
	genai,
	getRuntimeScope,
	pyaudio,
)

addonHandler.initTranslation()


MODEL_NAME = "gemini-2.5-flash-native-audio-preview-12-2025"
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
MEMORY_MAX_LINES = 12
MEMORY_MAX_CHARS = 1800


class TalkWithAIDialog(wx.Dialog):
	def __init__(self, parent, apiKey, voiceName, systemInstruction):
		# Translators: Title of the dialog for the "Talk With AI" feature (REAL-TIME conversation).
		super().__init__(parent, title=_("Talk With AI"), size=(400, 300))
		self.apiKey = apiKey
		self.voiceName = voiceName
		self.systemInstruction = systemInstruction

		self.client = None
		self.sessionActive = False
		self.loop = None
		self.loopThread = None
		self.audioInterface = None
		self.inputStream = None
		self.outputStream = None
		self.micOn = True

		self.audioQueue = queue.Queue()
		self.isPlaying = False
		self.playThread = None
		self.volume = 80  # Default volume percentage
		self.bufferThreshold = BUFFER_THRESHOLD
		self.lastBufferAdjustAt = 0.0
		self.lastStatusAt = 0.0
		self.memoryEnabled = True
		self.sessionMemory = []
		self.memoryLock = threading.Lock()

		# Audio Device Selection
		self.inputDevices = self._getDeviceList(input=True)
		self.outputDevices = self._getDeviceList(input=False)
		self.selectedInputIdx = None
		self.selectedOutputIdx = None

		self._buildUi()

		if not PYAUDIO_AVAILABLE:
			wx.CallAfter(
				self.reportError,
				_("PyAudio library is not installed. This feature requires PyAudio."),
			)
			self.connectBtn.Disable()
		if not GENAI_AVAILABLE:
			wx.CallAfter(self.reportError, _("Google GenAI library is not installed."))
			self.connectBtn.Disable()

		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

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
		except Exception as e:
			log.error(f"Error listing devices: {e}")
		finally:
			p.terminate()
		return devices

	def _buildUi(self):
		# Main Sizer
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		panel = wx.Panel(self)
		panelSizer = wx.BoxSizer(wx.VERTICAL)

		# 1. Status Area
		# Translators: Label for the status area showing connection state.
		statusBox = wx.StaticBox(panel, label=_("Status"))
		statusSizer = wx.StaticBoxSizer(statusBox, wx.VERTICAL)
		# Translators: Initial status message when the dialog opens.
		self.statusLabel = wx.StaticText(panel, label=_("Ready to Connect"))
		statusSizer.Add(self.statusLabel, 0, wx.ALL | wx.EXPAND, 5)
		panelSizer.Add(statusSizer, 0, wx.ALL | wx.EXPAND, 5)

		# 2. Controls Area
		controlsBox = wx.StaticBox(panel, label=_("Controls"))
		controlsSizer = wx.StaticBoxSizer(controlsBox, wx.VERTICAL)

		# Connect/Disconnect Buttons
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

		# Mic Toggle
		# Translators: Toggle button label indicating microphone is ON.
		self.micBtn = wx.ToggleButton(panel, label=_("Microphone: ON"))
		self.micBtn.SetValue(True)
		self.micBtn.Bind(wx.EVT_TOGGLEBUTTON, self.onMicToggle)
		controlsSizer.Add(self.micBtn, 0, wx.ALL | wx.EXPAND, 5)

		# Device Selection Sizer
		self.deviceSizer = wx.BoxSizer(wx.VERTICAL)

		# Input Device
		inputSizer = wx.BoxSizer(wx.HORIZONTAL)
		inputLabel = wx.StaticText(panel, label=_("Microphone:"))
		inputChoices = [d["name"] for d in self.inputDevices]
		self.inputChoice = wx.Choice(panel, choices=inputChoices)
		if inputChoices:
			self.inputChoice.SetSelection(0)
		inputSizer.Add(inputLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		inputSizer.Add(self.inputChoice, 1, wx.EXPAND)
		self.deviceSizer.Add(inputSizer, 0, wx.ALL | wx.EXPAND, 5)

		# Output Device
		outputSizer = wx.BoxSizer(wx.HORIZONTAL)
		outputLabel = wx.StaticText(panel, label=_("Speaker:"))
		outputChoices = [d["name"] for d in self.outputDevices]
		self.outputChoice = wx.Choice(panel, choices=outputChoices)
		if outputChoices:
			self.outputChoice.SetSelection(0)
		outputSizer.Add(outputLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		outputSizer.Add(self.outputChoice, 1, wx.EXPAND)
		self.deviceSizer.Add(outputSizer, 0, wx.ALL | wx.EXPAND, 5)

		controlsSizer.Add(self.deviceSizer, 0, wx.EXPAND)

		# Google Search Checkbox
		# Translators: Checkbox to enable "Grounding", allowing the AI to search Google for answers.
		self.googleSearchCb = wx.CheckBox(panel, label=_("Grounding with Google Search"))
		self.googleSearchCb.SetValue(False)
		controlsSizer.Add(self.googleSearchCb, 0, wx.ALL | wx.EXPAND, 5)

		# Translators: Checkbox to enable temporary conversation memory during this dialog session.
		self.memoryCb = wx.CheckBox(panel, label=_("Use session memory"))
		self.memoryCb.SetValue(True)
		self.memoryCb.Bind(wx.EVT_CHECKBOX, self.onMemoryToggle)
		controlsSizer.Add(self.memoryCb, 0, wx.ALL | wx.EXPAND, 5)

		# Translators: Button to clear temporary conversation memory for the current dialog session.
		self.clearMemoryBtn = wx.Button(panel, label=_("Clear memory now"))
		self.clearMemoryBtn.Bind(wx.EVT_BUTTON, self.onClearMemory)
		controlsSizer.Add(self.clearMemoryBtn, 0, wx.ALL | wx.EXPAND, 5)

		# Volume Slider
		volSizer = wx.BoxSizer(wx.HORIZONTAL)
		volLabel = wx.StaticText(panel, label=_("Volume:"))
		self.volSlider = wx.Slider(panel, value=self.volume, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
		self.volSlider.Bind(wx.EVT_SLIDER, self.onVolumeChange)

		volSizer.Add(volLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		volSizer.Add(self.volSlider, 1, wx.EXPAND)
		controlsSizer.Add(volSizer, 0, wx.ALL | wx.EXPAND, 5)

		panelSizer.Add(controlsSizer, 0, wx.ALL | wx.EXPAND, 5)

		# 3. Info Area (Voice only)
		# Translators: Label for the selected voice
		infoLabel = wx.StaticText(panel, label=_("Voice: ") + str(self.voiceName))
		panelSizer.Add(infoLabel, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

		panel.SetSizer(panelSizer)
		mainSizer.Add(panel, 1, wx.EXPAND)
		self.SetSizer(mainSizer)
		self.CenterOnParent()

	def updateStatus(self, text):
		if self:
			self.statusLabel.SetLabel(_("Status: ") + text)

	def reportError(self, msg):
		if self:
			wx.MessageBox(str(msg), _("Error"), wx.OK | wx.ICON_ERROR)
			self.updateStatus(_("Error"))

	def onMicToggle(self, evt):
		self.micOn = self.micBtn.GetValue()
		label = _("Microphone: ON") if self.micOn else _("Microphone: OFF")
		self.micBtn.SetLabel(label)

	def onVolumeChange(self, evt):
		self.volume = self.volSlider.GetValue()

	def onMemoryToggle(self, evt):
		self.memoryEnabled = self.memoryCb.GetValue()
		if not self.memoryEnabled:
			self._clearSessionMemory()
		if self.sessionActive:
			self.clearMemoryBtn.Hide()
		else:
			self.clearMemoryBtn.Show(self.memoryEnabled)
		self.Layout()

	def onClearMemory(self, evt):
		self._clearSessionMemory()
		self.updateStatus(_("Memory cleared"))

	def _clearSessionMemory(self):
		with self.memoryLock:
			self.sessionMemory = []

	def _rememberMemoryLine(self, line):
		if not line:
			return
		cleaned = str(line).strip()
		if not cleaned:
			return
		with self.memoryLock:
			self.sessionMemory.append(cleaned)
			if len(self.sessionMemory) > MEMORY_MAX_LINES:
				self.sessionMemory = self.sessionMemory[-MEMORY_MAX_LINES:]
			totalChars = sum(len(item) for item in self.sessionMemory)
			while self.sessionMemory and totalChars > MEMORY_MAX_CHARS:
				totalChars -= len(self.sessionMemory.pop(0))

	def _memorySummary(self):
		with self.memoryLock:
			if not self.sessionMemory:
				return ""
			return "\n".join(f"- {line}" for line in self.sessionMemory[-MEMORY_MAX_LINES:])

	def _buildSystemInstruction(self):
		baseRules = (
			"You are a voice assistant for blind and low-vision users. "
			"Never fabricate facts. If uncertain, explicitly say you are not sure."
		)
		userInstruction = self.systemInstruction.strip() if self.systemInstruction else ""
		parts = [baseRules]
		if userInstruction:
			parts.append(f"User preference:\n{userInstruction}")
		if self.memoryEnabled:
			summary = self._memorySummary()
			if summary:
				parts.append(f"Session memory:\n{summary}")
		return "\n\n".join(parts)

	def _buildReconnectDelay(self, attempt):
		baseDelay = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1)))
		return baseDelay + random.uniform(0.0, BACKOFF_JITTER_SECONDS)

	def onConnect(self, evt):
		self.connectBtn.Disable()
		self.disconnectBtn.Enable()

		# Store state and hide checkbox
		self.useGoogleSearch = self.googleSearchCb.GetValue()
		self.memoryEnabled = self.memoryCb.GetValue()
		if not self.memoryEnabled:
			self._clearSessionMemory()
		self.googleSearchCb.Hide()
		self.memoryCb.Disable()
		self.clearMemoryBtn.Hide()

		# Get selected devices
		inSel = self.inputChoice.GetSelection()
		if inSel != wx.NOT_FOUND and self.inputDevices:
			self.selectedInputIdx = self.inputDevices[inSel]["index"]

		outSel = self.outputChoice.GetSelection()
		if outSel != wx.NOT_FOUND and self.outputDevices:
			self.selectedOutputIdx = self.outputDevices[outSel]["index"]

		# Hide device selection widgets
		for child in self.deviceSizer.GetChildren():
			w = child.GetWindow()
			if w:
				w.Hide()
			s = child.GetSizer()
			if s:
				for c in s.GetChildren():
					w2 = c.GetWindow()
					if w2:
						w2.Hide()

		self.Layout()

		self.updateStatus(_("Connecting..."))

		self.sessionActive = True
		self.loopThread = threading.Thread(target=self._startAsyncLoop, daemon=True)
		self.loopThread.start()

	def onDisconnect(self, evt):
		self.disconnectBtn.Disable()
		self.updateStatus(_("Disconnecting..."))
		# Sound is played in runSession finally block
		if self.loop and self.loop.is_running():
			asyncio.run_coroutine_threadsafe(self.cleanupAsync(), self.loop)

	def _playSoundEffect(self, path):
		"""Plays a local sound file asynchronously."""

		def _bgPlay():
			try:
				if os.path.exists(path):
					winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
			except Exception:
				pass

		threading.Thread(target=_bgPlay, daemon=True).start()

	def onCharHook(self, evt):
		if evt.GetKeyCode() == wx.WXK_ESCAPE:
			self.Close()
		else:
			evt.Skip()

	def onClose(self, evt: wx.Event):
		self.sessionActive = False
		self.isPlaying = False
		self._clearSessionMemory()

		# Drain and clear audio queue
		while not self.audioQueue.empty():
			try:
				self.audioQueue.get_nowait()
			except queue.Empty:
				pass
		self.audioQueue.put(b"")

		if self.loop and self.loop.is_running():
			try:
				# Schedule cleanup and wait for it
				future = asyncio.run_coroutine_threadsafe(self.cleanupAsync(), self.loop)
				# Wait briefly for cleanup to run
				try:
					future.result(timeout=2.0)
				except Exception:
					pass

				# Signal loop to stop
				self.loop.call_soon_threadsafe(self.loop.stop)
			except Exception:
				pass

		if self.audioInterface:
			try:
				self.audioInterface.terminate()
			except Exception:
				pass

		self.Destroy()

	def _startAsyncLoop(self):
		try:
			self.loop = asyncio.new_event_loop()
			asyncio.set_event_loop(self.loop)
			self.loop.run_until_complete(self.runSession())
		except RuntimeError:
			# Loop stopped cleanly or forcefully
			pass
		except Exception as e:
			log.error(f"Async Loop Error: {e}", exc_info=True)
		finally:
			try:
				# Cancel all remaining tasks specific to this loop
				pending = asyncio.all_tasks(self.loop)
				for task in pending:
					task.cancel()

				# Allow cancellations to process
				if pending and not self.loop.is_closed():
					self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

				if not self.loop.is_closed():
					self.loop.close()
			except Exception:
				pass

	async def cleanupAsync(self):
		self.sessionActive = False
		self.isPlaying = False

		# Cancel all tasks in the current loop to force exits
		currentTask = asyncio.current_task()
		for task in asyncio.all_tasks():
			if task is not currentTask:
				task.cancel()

		# Drain queue
		while not self.audioQueue.empty():
			try:
				self.audioQueue.get_nowait()
			except Exception:
				pass

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
		"""
		Thread that consumes audio chunks from the queue, applies volume, and plays them.
		"""
		buffer = []
		buffering = True
		self.bufferThreshold = BUFFER_THRESHOLD

		while self.sessionActive and self.isPlaying:
			try:
				# Wait for data
				data = self.audioQueue.get(timeout=0.1)

				# Apply Volume
				if self.volume != 100:
					# Parse 16-bit PCM (signed)
					count = len(data) // 2
					shorts = struct.unpack(f"{count}h", data)

					# Apply scale factor (0.0 to 1.0)
					factor = self.volume / 100.0

					# Scale and clip
					scaledShorts = []
					for s in shorts:
						val = int(s * factor)
						# Clip to 16-bit range
						if val > 32767:
							val = 32767
						if val < -32768:
							val = -32768
						scaledShorts.append(val)

					data = struct.pack(f"{count}h", *scaledShorts)

				if buffering:
					buffer.append(data)
					if len(buffer) >= self.bufferThreshold:
						buffering = False
						# Play accumulated buffer
						if self.outputStream and self.outputStream.is_active():
							for chunk in buffer:
								self.outputStream.write(chunk)
						buffer = []
				else:
					# Direct play
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
				# If queue is empty, we have run out of audio data.
				# To prevent micro-stuttering, we switch back to buffering mode.
				if not buffering and self.sessionActive:
					buffering = True
					now = time.monotonic()
					if self.bufferThreshold < MAX_BUFFER_THRESHOLD and now - self.lastBufferAdjustAt > 0.8:
						self.bufferThreshold += 1
						self.lastBufferAdjustAt = now
				continue
			except Exception as e:
				log.error(f"Audio Player Error: {e}")
				break

	async def sendAudioLoop(self, session):
		while self.sessionActive:
			if self.micOn and self.inputStream and self.inputStream.is_active():
				try:
					data = await self.loop.run_in_executor(
						None,
						lambda: self.inputStream.read(CHUNK, exception_on_overflow=False),
					)
					await session.send(
						input={"data": data, "mime_type": f"audio/pcm;rate={INPUT_RATE}"},
						end_of_turn=False,
					)
				except Exception as e:
					log.error(f"Mic/Send Error: {e}")
					break
			else:
				await asyncio.sleep(0.1)

	async def receiveLoop(self, session):
		try:
			async for response in session.receive():
				if not self.sessionActive:
					break

				if response.server_content is None:
					continue

				# Handle Interruption
				if response.server_content.interrupted:
					log.debug("TalkWithAI: Server Interrupted")
					# Clear audio queue to stop playing immediately
					# This prevents "echo" loop where model hears its own delayed speech
					while not self.audioQueue.empty():
						try:
							self.audioQueue.get_nowait()
						except queue.Empty:
							break
					continue

				# Handle Turn Complete
				if response.server_content.turn_complete:
					log.debug("TalkWithAI: Turn Complete")
					continue

				inputTranscription = getattr(response.server_content, "input_transcription", None)
				if inputTranscription and getattr(inputTranscription, "text", None):
					self._rememberMemoryLine(f"User: {inputTranscription.text}")

				outputTranscription = getattr(response.server_content, "output_transcription", None)
				if outputTranscription and getattr(outputTranscription, "text", None):
					self._rememberMemoryLine(f"Assistant: {outputTranscription.text}")

				modelTurn = response.server_content.model_turn
				if modelTurn is not None:
					for part in modelTurn.parts:
						if part.inline_data is not None:
							audioData = part.inline_data.data
							# Push to queue instead of writing directly
							self.audioQueue.put(audioData)
						textPart = getattr(part, "text", None)
						if textPart:
							self._rememberMemoryLine(f"Assistant: {textPart}")
		except Exception as e:
			log.error(f"TalkWithAI Receive Loop Error: {e}")
		finally:
			log.debug("TalkWithAI: Receive loop ended")
			# Do NOT set self.sessionActive = False here.
			# Doing so would stop the reconnection loop in runSession.

	async def runSession(self):
		try:
			# Setup Audio (Once for the entire session duration)
			with getRuntimeScope():
				self.audioInterface = pyaudio.PyAudio()

			# Output Stream (Speaker)
			self.outputStream = self.audioInterface.open(
				format=FORMAT,
				channels=CHANNELS,
				rate=OUTPUT_RATE,
				output=True,
				frames_per_buffer=CHUNK,
				output_device_index=self.selectedOutputIdx,
			)

			# Input Stream (Mic)
			self.inputStream = self.audioInterface.open(
				format=FORMAT,
				channels=CHANNELS,
				rate=INPUT_RATE,
				input=True,
				frames_per_buffer=CHUNK,
				input_device_index=self.selectedInputIdx,
			)

			# Initialize Client
			with getRuntimeScope():
				self.client = genai.Client(api_key=self.apiKey, http_options={"api_version": "v1alpha"})

			firstConnect = True
			retryAttempt = 0

			# Main Reconnection Loop
			while self.sessionActive:
				try:
					toolsConfig = []
					if self.useGoogleSearch:
						toolsConfig.append({"google_search": {}})
					systemInstruction = self._buildSystemInstruction()
					config = {
						"response_modalities": ["AUDIO"],
						"tools": toolsConfig,
						"generation_config": {
							"speech_config": {
								"voice_config": {"prebuilt_voice_config": {"voice_name": self.voiceName}},
							},
						},
						"system_instruction": {"parts": [{"text": systemInstruction}]},
					}
					log.debug("TalkWithAI: Connecting to Gemini Live...")
					with getRuntimeScope():
						async with self.client.aio.live.connect(model=MODEL_NAME, config=config) as session:
							retryAttempt = 0
							if firstConnect:
								wx.CallAfter(self.updateStatus, _("Connected"))
								# Play start sound only on the very first successful connection
								self._playSoundEffect(STREAM_START_SOUND_PATH)
								firstConnect = False
							else:
								log.debug("TalkWithAI: Reconnected silently")

							self.session = session

							# Start sending and receiving tasks
							sendTask = asyncio.create_task(self.sendAudioLoop(session))
							receiveTask = asyncio.create_task(self.receiveLoop(session))

							if not self.isPlaying:
								playWorker = threading.Thread(target=self._audioPlayerWorker, daemon=True)
								self.isPlaying = True
								playWorker.start()

							# Wait for either task to finish
							# If connection drops, receiveLoop finishes.
							# We then cancel sendTask and reconnect.
							_done, pending = await asyncio.wait(
								[sendTask, receiveTask],
								return_when=asyncio.FIRST_COMPLETED,
							)

							# Cancel pending tasks (e.g. send loop if receive died)
							for task in pending:
								task.cancel()
								try:
									await task
								except asyncio.CancelledError:
									pass

				except Exception as e:
					log.error(f"TalkWithAI Session/Connection Error: {e}")
					retryAttempt += 1
					delay = self._buildReconnectDelay(retryAttempt)
					now = time.monotonic()
					if now - self.lastStatusAt > 1.0:
						wx.CallAfter(
							self.updateStatus,
							_("Connection lost. Retrying in {seconds:.1f}s").format(seconds=delay),
						)
						self.lastStatusAt = now
					await asyncio.sleep(delay)

				if self.sessionActive:
					log.debug("TalkWithAI: Reconnecting...")

		except asyncio.CancelledError:
			pass
		except Exception as e:
			log.error(f"TalkWithAI Fatal Error: {traceback.format_exc()}")
			wx.CallAfter(self.reportError, str(e))
			self.sessionActive = False
		finally:
			# Play end sound only when completely stopping
			self._playSoundEffect(STREAM_END_SOUND_PATH)

			wx.CallAfter(self.resetUi)
			# Cleanup Audio
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

	def resetUi(self):
		if self:
			try:
				self.connectBtn.Enable()
				self.disconnectBtn.Disable()
				self.googleSearchCb.Show()
				self.memoryCb.Enable()
				self.clearMemoryBtn.Show(self.memoryCb.GetValue())

				# Show device selection again
				for child in self.deviceSizer.GetChildren():
					w = child.GetWindow()
					if w:
						w.Show()
					s = child.GetSizer()
					if s:
						for c in s.GetChildren():
							w2 = c.GetWindow()
							if w2:
								w2.Show()

				self.Layout()
				self.updateStatus(_("Ready"))
			except RuntimeError:
				pass  # Window might be destroyed
