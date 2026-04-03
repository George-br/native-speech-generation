# -*- coding: utf-8 -*-
import wx
import webbrowser
import os
import shutil
import time
from typing import TYPE_CHECKING
import gui
import addonHandler
from logHandler import log

from .. import lib_updater
from ..core import config_store

if TYPE_CHECKING:

	def _(msg: str) -> str:
		return msg


# Initialize translation
addonHandler.initTranslation()


class NativeSpeechSettingsPanel(gui.settingsDialogs.SettingsPanel):
	# Translators: Title of the settings panel in NVDA preferences.
	title = _("Native Speech Generation")

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self._validatedApiKeyValue = ""
		self._validatedEncryptedApiKey = ""

	def makeSettings(self, settingsSizer: wx.Sizer) -> None:
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		apiResolution = config_store.resolve_api_key()

		# API Key Configuration Group
		apiSizer = wx.BoxSizer(wx.HORIZONTAL)

		# Translators: Label for the input field where user enters their Gemini API Key.
		apiLabel = wx.StaticText(self, label=_("&Gemini API Key:"))
		apiSizer.Add(apiLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

		apiValue = config_store.get_stored_api_key()

		self.apiKeyCtrlHidden = wx.TextCtrl(self, value=apiValue, style=wx.TE_PASSWORD)
		self.apiKeyCtrlVisible = wx.TextCtrl(self, value=apiValue)
		self.apiKeyCtrlVisible.Hide()

		# Add inputs with EXPAND to fill available space
		apiSizer.Add(self.apiKeyCtrlHidden, 1, wx.EXPAND | wx.RIGHT, 5)
		apiSizer.Add(self.apiKeyCtrlVisible, 1, wx.EXPAND | wx.RIGHT, 5)

		# Translators: Checkbox to toggle visibility of the API key (show/hide characters).
		self.showApiCheck = wx.CheckBox(self, label=_("Show API Key"))
		self.showApiCheck.Bind(wx.EVT_CHECKBOX, self.onToggleApiVisibility)
		apiSizer.Add(self.showApiCheck, 0, wx.ALIGN_CENTER_VERTICAL)

		# Add the row to the main settings sizer
		settingsSizer.Add(apiSizer, 0, wx.EXPAND | wx.ALL, 5)
		self.onToggleApiVisibility(None)  # Set initial state

		apiInfoMessage = self._getApiKeyInfoMessage(apiResolution)
		self.apiKeyInfoLabel = sHelper.addItem(wx.StaticText(self, label=apiInfoMessage))
		if apiInfoMessage:
			self.apiKeyInfoLabel.Wrap(560)
		else:
			self.apiKeyInfoLabel.Hide()

		# Translators: Button starting a process to help user get an API key (opens a website).
		self.getKeyBtn = wx.Button(self, label=_("&How to get API Key..."))
		sHelper.addItem(self.getKeyBtn)
		self.getKeyBtn.Bind(wx.EVT_BUTTON, self.onGetKey)

		# Reinstall libraries button
		# Translators: Button to force a reinstallation of external dependencies (Python libraries).
		self.reinstallBtn = wx.Button(self, label=_("&Reinstall Libraries"))
		sHelper.addItem(self.reinstallBtn)
		self.reinstallBtn.Bind(wx.EVT_BUTTON, self.onReinstall)

	def _getApiKeyInfoMessage(self, resolution: config_store.ApiKeyResolution) -> str:
		if resolution.status == "undecryptable" and resolution.source == "environment":
			# Translators: Information shown in settings when a stored key cannot be decrypted
			# and the add-on is using GEMINI_API_KEY from the environment instead.
			return _(
				"The stored API key could not be decrypted on this Windows user or machine. "
				"Using {envVarName} from the environment instead. Enter a new key here to replace it.",
			).format(envVarName=config_store.API_KEY_ENV_VAR)
		if resolution.status == "undecryptable":
			# Translators: Information shown in settings when a stored key cannot be decrypted.
			return _(
				"The stored API key could not be decrypted on this Windows user or machine. "
				"Enter a new key here, or set {envVarName} in the environment.",
			).format(envVarName=config_store.API_KEY_ENV_VAR)
		if resolution.source == "environment":
			# Translators: Information shown in settings when the add-on is using GEMINI_API_KEY
			# from the environment because no stored key is available.
			return _(
				"Using {envVarName} from the environment. Saving a key here will override it.",
			).format(envVarName=config_store.API_KEY_ENV_VAR)
		return ""

	def onToggleApiVisibility(self, event: wx.Event | None) -> None:
		if self.showApiCheck.IsChecked():
			self.apiKeyCtrlVisible.SetValue(self.apiKeyCtrlHidden.GetValue())
			self.apiKeyCtrlHidden.Hide()
			self.apiKeyCtrlVisible.Show()
		else:
			self.apiKeyCtrlHidden.SetValue(self.apiKeyCtrlVisible.GetValue())
			self.apiKeyCtrlVisible.Hide()
			self.apiKeyCtrlHidden.Show()
		self.Layout()

	def onGetKey(self, evt: wx.Event) -> None:
		webbrowser.open("https://aistudio.google.com/apikey")

	def _getCurrentApiKeyFieldValue(self) -> str:
		return (
			self.apiKeyCtrlVisible.GetValue()
			if self.showApiCheck.IsChecked()
			else self.apiKeyCtrlHidden.GetValue()
		)

	def _showStorageError(self, error: config_store.ApiKeyStorageError) -> None:
		log.error(f"Failed to store the Gemini API key securely: {error}", exc_info=True)
		wx.MessageBox(
			# Translators: Error shown if Windows DPAPI storage fails while saving the API key.
			_("Failed to save the Gemini API key securely: {error}").format(error=str(error)),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
		)

	def isValid(self) -> bool:
		try:
			self._validatedApiKeyValue, self._validatedEncryptedApiKey = config_store.prepare_api_key_for_storage(
				self._getCurrentApiKeyFieldValue(),
			)
		except config_store.ApiKeyStorageError as error:
			self._validatedApiKeyValue = ""
			self._validatedEncryptedApiKey = ""
			self._showStorageError(error)
			return False
		return True

	def onReinstall(self, evt: wx.Event) -> None:
		"""Handles the reinstall libraries action."""
		res = wx.MessageBox(
			_("This will delete the existing library and restart NVDA to redownload it.\nAre you sure?"),
			_("Confirm Reinstall"),
			wx.OK | wx.CANCEL | wx.ICON_WARNING,
		)
		if res != wx.OK:
			return

		try:
			# Try to get LIB_DIR from lib_updater, fallback if needed
			try:
				targetLib = lib_updater.LIB_DIR
			except AttributeError:
				# Fallback calculation matching __init__.py logic if lib_updater fails
				# This path calculation assumes we are in gui/settings.py
				# And we want .../globalPlugins/NativeSpeechGeneration/lib
				guiDir = os.path.dirname(os.path.abspath(__file__))
				pkgDir = os.path.dirname(guiDir)
				targetLib = os.path.join(pkgDir, "lib")

			if os.path.exists(targetLib):
				# Rename first to avoid lock issues, let cleanupTrash handle deletion on next run
				tempTrash = targetLib + "_trash_" + str(time.time())
				os.rename(targetLib, tempTrash)
				# Try to delete immediately, but ignore errors if locked
				shutil.rmtree(tempTrash, ignore_errors=True)

			wx.MessageBox(
				_("Library removed successfully. NVDA will now restart to download the latest version."),
				_("Restart Required"),
				wx.OK | wx.ICON_INFORMATION,
			)
			import core

			core.restart()

		except Exception as e:
			log.error(f"Failed to delete lib folder: {e}", exc_info=True)
			wx.MessageBox(
				f"Failed to remove library: {e}\nPlease check log.",
				_("Error"),
				wx.OK | wx.ICON_ERROR,
			)

	def onSave(self) -> None:
		if not self.isValid():
			return
		try:
			config_store.write_prepared_api_key(
				self._validatedApiKeyValue,
				self._validatedEncryptedApiKey,
			)
		except config_store.ApiKeyStorageError as error:
			self._showStorageError(error)
