# -*- coding: utf-8 -*-
import base64
import ctypes
import os
from dataclasses import dataclass
from typing import Any, Final, Literal

import config
from logHandler import log

from .constants import CONFIG_DOMAIN

API_KEY_ENV_VAR: Final[str] = "GEMINI_API_KEY"
_DPAPI_DESCRIPTION: Final[str] = "Native Speech Generation API Key"
_CRYPTPROTECT_UI_FORBIDDEN: Final[int] = 0x1
_CONFIG_SPEC: Final[dict[str, str]] = {
	"apiKey": "string(default='')",
	"apiKeyEncrypted": "string(default='')",
}

ApiKeySource = Literal["stored", "environment", "missing"]
ApiKeyStatus = Literal["stored", "environment", "missing", "undecryptable", "legacyMigrated"]


@dataclass(frozen=True)
class ApiKeyResolution:
	value: str
	source: ApiKeySource
	status: ApiKeyStatus


class ApiKeyStorageError(RuntimeError):
	pass


class _DATA_BLOB(ctypes.Structure):
	_fields_ = [
		("cbData", ctypes.c_uint32),
		("pbData", ctypes.POINTER(ctypes.c_ubyte)),
	]


def register_config_spec() -> None:
	config.conf.spec[CONFIG_DOMAIN] = _CONFIG_SPEC.copy()
	_get_config_section()


def prepare_config_for_startup(*, persist: bool) -> bool:
	register_config_spec()
	removedLegacyPlaintext = _remove_legacy_plaintext_if_encrypted_exists()
	migratedLegacyPlaintext = _migrate_plaintext_api_key()
	if persist and (removedLegacyPlaintext or migratedLegacyPlaintext):
		config.save()
	return removedLegacyPlaintext or migratedLegacyPlaintext


def get_stored_api_key() -> str:
	prepare_config_for_startup(persist=False)
	encryptedValue = _get_text_setting("apiKeyEncrypted").strip()
	if not encryptedValue:
		return ""
	try:
		return _decrypt_api_key(encryptedValue)
	except ApiKeyStorageError as error:
		log.warning(f"Stored encrypted Gemini API key could not be decrypted: {error}")
		return ""


def prepare_api_key_for_storage(value: str) -> tuple[str, str]:
	cleanValue = value.strip()
	if not cleanValue:
		return "", ""
	return cleanValue, _encrypt_api_key(cleanValue)


def write_prepared_api_key(cleanValue: str, encryptedValue: str) -> None:
	register_config_spec()
	if not cleanValue:
		_set_text_setting("apiKeyEncrypted", "")
		_set_text_setting("apiKey", "")
		return
	_set_text_setting("apiKeyEncrypted", encryptedValue)
	_set_text_setting("apiKey", "")


def set_stored_api_key(value: str) -> None:
	cleanValue, encryptedValue = prepare_api_key_for_storage(value)
	write_prepared_api_key(cleanValue, encryptedValue)


def resolve_api_key() -> ApiKeyResolution:
	migratedLegacyPlaintext = prepare_config_for_startup(persist=False)
	encryptedValue = _get_text_setting("apiKeyEncrypted").strip()
	if encryptedValue:
		try:
			return ApiKeyResolution(
				value=_decrypt_api_key(encryptedValue),
				source="stored",
				status="legacyMigrated" if migratedLegacyPlaintext else "stored",
			)
		except ApiKeyStorageError as error:
			log.warning(f"Stored encrypted Gemini API key could not be decrypted: {error}")
			environmentValue = _get_environment_api_key()
			if environmentValue:
				return ApiKeyResolution(
					value=environmentValue,
					source="environment",
					status="undecryptable",
				)
			return ApiKeyResolution(value="", source="missing", status="undecryptable")

	environmentValue = _get_environment_api_key()
	if environmentValue:
		return ApiKeyResolution(value=environmentValue, source="environment", status="environment")
	return ApiKeyResolution(value="", source="missing", status="missing")


def _get_environment_api_key() -> str:
	return os.environ.get(API_KEY_ENV_VAR, "").strip()


def _get_config_section() -> Any:
	return config.conf[CONFIG_DOMAIN]


def _get_text_setting(name: str) -> str:
	value = _get_config_section().get(name, "")
	return value if isinstance(value, str) else str(value or "")


def _set_text_setting(name: str, value: str) -> None:
	_get_config_section()[name] = value


def _remove_legacy_plaintext_if_encrypted_exists() -> bool:
	legacyValue = _get_text_setting("apiKey").strip()
	encryptedValue = _get_text_setting("apiKeyEncrypted").strip()
	if not (legacyValue and encryptedValue):
		return False
	_set_text_setting("apiKey", "")
	log.info("Removed legacy plaintext Gemini API key from configuration.")
	return True


def _migrate_plaintext_api_key() -> bool:
	legacyValue = _get_text_setting("apiKey").strip()
	encryptedValue = _get_text_setting("apiKeyEncrypted").strip()
	if not legacyValue or encryptedValue:
		return False
	try:
		_set_text_setting("apiKeyEncrypted", _encrypt_api_key(legacyValue))
	except ApiKeyStorageError:
		log.error("Failed to migrate the legacy plaintext Gemini API key to encrypted storage.", exc_info=True)
		return False
	_set_text_setting("apiKey", "")
	log.info("Migrated legacy plaintext Gemini API key to DPAPI-protected storage.")
	return True


def _encrypt_api_key(value: str) -> str:
	if not value:
		return ""
	try:
		protectedValue = _protect_bytes_with_dpapi(value.encode("utf-8"))
	except Exception as error:
		raise ApiKeyStorageError("Failed to encrypt the API key with Windows DPAPI.") from error
	return base64.b64encode(protectedValue).decode("ascii")


def _decrypt_api_key(value: str) -> str:
	if not value:
		return ""
	try:
		protectedValue = base64.b64decode(value.encode("ascii"), validate=True)
	except Exception as error:
		raise ApiKeyStorageError("Stored API key data is not valid base64.") from error
	try:
		plainValue = _unprotect_bytes_with_dpapi(protectedValue)
	except Exception as error:
		raise ApiKeyStorageError(
			"Stored API key data could not be decrypted for this Windows user or machine.",
		) from error
	try:
		return plainValue.decode("utf-8")
	except UnicodeDecodeError as error:
		raise ApiKeyStorageError("Stored API key data is not valid UTF-8 text.") from error


def _protect_bytes_with_dpapi(value: bytes) -> bytes:
	try:
		import win32crypt
	except ImportError:
		return _protect_bytes_with_ctypes(value)
	return win32crypt.CryptProtectData(
		value,
		_DPAPI_DESCRIPTION,
		None,
		None,
		None,
		_CRYPTPROTECT_UI_FORBIDDEN,
	)


def _unprotect_bytes_with_dpapi(value: bytes) -> bytes:
	try:
		import win32crypt
	except ImportError:
		return _unprotect_bytes_with_ctypes(value)
	_description, plainValue = win32crypt.CryptUnprotectData(
		value,
		None,
		None,
		None,
		_CRYPTPROTECT_UI_FORBIDDEN,
	)
	return plainValue


def _protect_bytes_with_ctypes(value: bytes) -> bytes:
	dataIn, inputBuffer = _create_data_blob(value)
	dataOut = _DATA_BLOB()
	crypt32, _kernel32 = _load_dpapi_libraries()
	del inputBuffer
	if not crypt32.CryptProtectData(
		ctypes.byref(dataIn),
		_DPAPI_DESCRIPTION,
		None,
		None,
		None,
		_CRYPTPROTECT_UI_FORBIDDEN,
		ctypes.byref(dataOut),
	):
		raise ctypes.WinError(ctypes.get_last_error())
	return _copy_and_free_data_blob(dataOut)


def _unprotect_bytes_with_ctypes(value: bytes) -> bytes:
	dataIn, inputBuffer = _create_data_blob(value)
	dataOut = _DATA_BLOB()
	crypt32, _kernel32 = _load_dpapi_libraries()
	del inputBuffer
	if not crypt32.CryptUnprotectData(
		ctypes.byref(dataIn),
		None,
		None,
		None,
		None,
		_CRYPTPROTECT_UI_FORBIDDEN,
		ctypes.byref(dataOut),
	):
		raise ctypes.WinError(ctypes.get_last_error())
	return _copy_and_free_data_blob(dataOut)


def _create_data_blob(value: bytes) -> tuple[_DATA_BLOB, ctypes.Array[ctypes.c_char] | None]:
	if not value:
		return _DATA_BLOB(0, ctypes.POINTER(ctypes.c_ubyte)()), None
	buffer = ctypes.create_string_buffer(value, len(value))
	return _DATA_BLOB(
		len(value),
		ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
	), buffer


def _copy_and_free_data_blob(blob: _DATA_BLOB) -> bytes:
	_crypt32, kernel32 = _load_dpapi_libraries()
	try:
		if not blob.cbData or not blob.pbData:
			return b""
		return ctypes.string_at(blob.pbData, blob.cbData)
	finally:
		if blob.pbData:
			kernel32.LocalFree(ctypes.cast(blob.pbData, ctypes.c_void_p))


def _load_dpapi_libraries() -> tuple[ctypes.WinDLL, ctypes.WinDLL]:
	crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
	kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
	crypt32.CryptProtectData.argtypes = (
		ctypes.POINTER(_DATA_BLOB),
		ctypes.c_wchar_p,
		ctypes.POINTER(_DATA_BLOB),
		ctypes.c_void_p,
		ctypes.c_void_p,
		ctypes.c_uint32,
		ctypes.POINTER(_DATA_BLOB),
	)
	crypt32.CryptProtectData.restype = ctypes.c_int
	crypt32.CryptUnprotectData.argtypes = (
		ctypes.POINTER(_DATA_BLOB),
		ctypes.POINTER(ctypes.c_wchar_p),
		ctypes.POINTER(_DATA_BLOB),
		ctypes.c_void_p,
		ctypes.c_void_p,
		ctypes.c_uint32,
		ctypes.POINTER(_DATA_BLOB),
	)
	crypt32.CryptUnprotectData.restype = ctypes.c_int
	kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
	kernel32.LocalFree.restype = ctypes.c_void_p
	return crypt32, kernel32
