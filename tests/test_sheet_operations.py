import os
from dataclasses import asdict
from typing import Dict, List
from unittest.mock import Mock, patch

from freezegun import freeze_time
from gspread import Spreadsheet, Worksheet
from oauth2client.service_account import ServiceAccountCredentials

from allocate_reviewers import (
    DRIVE_SCOPE,
    Developer,
    get_remote_sheet,
    load_developers_from_sheet,
    write_exception_to_sheet,
    write_reviewers_to_sheet,
)
from tests.conftest import SHEET
from tests.utils import mutate_devs


@patch.dict(os.environ, {"CREDENTIAL_FILE": "credential_file.json", "SHEET_NAME": "S"})
@patch("allocate_reviewers.ServiceAccountCredentials")
@patch("allocate_reviewers.gspread")
def test_get_remote_sheet(mocked_gspread: Mock, mocked_service_account: Mock) -> None:
    mocked_credential = Mock(spec=ServiceAccountCredentials)
    mocked_service_account.from_json_keyfile_name.return_value = mocked_credential

    mocked_client = Mock()
    mocked_gspread.authorize.return_value = mocked_client

    mocked_spreadsheet = Mock(spec=Spreadsheet)
    mocked_client.open.return_value = mocked_spreadsheet

    with get_remote_sheet() as sheet:
        mocked_service_account.from_json_keyfile_name.assert_called_once_with(
            "credential_file.json", DRIVE_SCOPE
        )
        mocked_gspread.authorize.assert_called_once_with(mocked_credential)

        mocked_client.open.assert_called_once_with("S")
        assert sheet == mocked_spreadsheet.sheet1

        mocked_client.session.close.assert_not_called()

    mocked_client.session.close.assert_called_once()


def test_load_developers_from_sheet(
    mocked_sheet_data: List[Dict[str, str]], mocked_devs: List[Developer]
) -> None:

    devs = load_developers_from_sheet()
    assert len(devs) == 5
    for idx, dev in enumerate(devs):
        assert asdict(dev) == asdict(mocked_devs[idx])


@freeze_time("2022-09-25 12:12:12")
def test_write_reviewers_to_sheet(
    mocked_sheet: Worksheet, mocked_devs: List[Developer]
) -> None:
    DEV_REVIEWERS_MAPPER = {
        "B": set(("C", "D")),
        "E": set(("C", "A")),
    }
    mutate_devs(mocked_devs, "reviewer_names", DEV_REVIEWERS_MAPPER)
    new_column = [["25-09-2022", "", "C, D", "", "", "A, C"]]

    mocked_sheet.get_all_records.return_value = SHEET
    write_reviewers_to_sheet(mocked_devs)

    mocked_sheet.insert_cols.assert_called_once_with(new_column, 4)


@freeze_time("2022-09-30 12:12:12")
def test_write_exception_to_sheet(mocked_sheet: Worksheet) -> None:
    new_column = [["Exception 30-09-2022", "Awesome error!"]]

    write_exception_to_sheet("Awesome error!")

    mocked_sheet.insert_cols.assert_called_once_with(new_column, 4)
