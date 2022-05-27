import platform
from urllib import request
import tempfile
import subprocess
import os
import logging

from module.instrument.api_requester import ApiRequester
from module.recipe import compare_versions
from module.recipe import check_internet

LATEST_VERSION = "0.0"
PREPARED_VERSION = "0.0"
IS_PREPARED = False


def get_status():
    return IS_PREPARED


def prepare():

    global LATEST_VERSION
    global PREPARED_VERSION
    global IS_PREPARED

    if not check_internet.connected():
        return

    api_requester = ApiRequester()
    payload = {"id": "version"}
    response = api_requester.cunarist("GET", "/api/solsol/latest-information", payload)
    LATEST_VERSION = response["value"]

    with open("./resource/version.txt", mode="r", encoding="utf8") as file:
        current_version = file.read()

    if IS_PREPARED:

        temp_folder = tempfile.gettempdir()

        if platform.system() == "Windows":
            filepath = temp_folder + "/SolsolWindowsSetup.exe"
        elif platform.system() == "Linux":
            pass
        elif platform.system() == "Darwin":  # macOS
            pass

        if not os.path.isfile(filepath):
            # when temp directory is cleaned up for some reason...
            IS_PREPARED = False
            PREPARED_VERSION = "0.0"

    if compare_versions.do(LATEST_VERSION, current_version):

        if not compare_versions.do(LATEST_VERSION, PREPARED_VERSION):
            return

        platform_system = platform.system()

        if platform_system == "Windows":
            platform_name = "Windows"
        elif platform_system == "Linux":
            platform_name = "Linux"
        elif platform_system == "Darwin":
            platform_name = "macOS"

        blob_name = f"Solsol{platform_name}Setup.exe"

        api_requester = ApiRequester()

        payload = {"blobName": blob_name}
        response = api_requester.cunarist("GET", "/api/solsol/installer-url", payload)
        blob_url = response["blobUrl"]

        download_data = request.urlopen(blob_url).read()
        temp_folder = tempfile.gettempdir()

        if platform.system() == "Windows":
            filepath = temp_folder + "/SolsolWindowsSetup.exe"
        elif platform.system() == "Linux":
            pass
        elif platform.system() == "Darwin":  # macOS
            pass

        with open(filepath, mode="wb") as file:
            file.write(download_data)

        text = "업데이트 설치 파일을 다운로드해서 준비했습니다."
        logger = logging.getLogger("solsol")
        logger.info(text)

        PREPARED_VERSION = LATEST_VERSION
        IS_PREPARED = True


def apply():

    if IS_PREPARED:

        if platform.system() == "Windows":
            temp_folder = tempfile.gettempdir()
            filepath = temp_folder + "/SolsolWindowsSetup.exe"
            if os.path.isfile(filepath):
                commands = [f"{filepath} /SILENT"]
                subprocess.Popen(
                    "&&".join(commands),
                    creationflags=subprocess.DETACHED_PROCESS,
                )

        elif platform.system() == "Linux":
            pass

        elif platform.system() == "Darwin":  # macOS
            pass
