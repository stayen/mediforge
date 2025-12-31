"""Tests for timecode parsing and formatting."""

from decimal import Decimal

import pytest

from mediforge.core.timecode import parse_timecode, format_timecode, parse_duration


class TestParseTimecode:
    """Tests for parse_timecode function."""

    def test_full_format_with_hours(self):
        """Test parsing H:MM:SS.mmm format."""
        assert parse_timecode("1:23:45.678") == Decimal("5025.678")

    def test_minutes_seconds_milliseconds(self):
        """Test parsing M:SS.mmm format."""
        assert parse_timecode("5:30.500") == Decimal("330.5")

    def test_seconds_milliseconds(self):
        """Test parsing SS.mmm format."""
        assert parse_timecode("45.123") == Decimal("45.123")

    def test_no_milliseconds(self):
        """Test parsing without milliseconds."""
        assert parse_timecode("1:30:00") == Decimal("5400")
        assert parse_timecode("5:30") == Decimal("330")

    def test_zero_timecode(self):
        """Test parsing zero timecode."""
        assert parse_timecode("0:00:00.000") == Decimal("0")
        assert parse_timecode("0:00") == Decimal("0")

    def test_leading_zeros(self):
        """Test parsing with leading zeros."""
        assert parse_timecode("0:05:03.001") == Decimal("303.001")

    def test_single_digit_milliseconds(self):
        """Test that single digit milliseconds are handled correctly."""
        # "0:00:01.1" should be 1.1 seconds, not 1.001
        assert parse_timecode("0:00:01.1") == Decimal("1.1")

    def test_two_digit_milliseconds(self):
        """Test that two digit milliseconds are handled correctly."""
        assert parse_timecode("0:00:01.12") == Decimal("1.12")

    def test_just_seconds(self):
        """Test parsing just seconds."""
        assert parse_timecode("45") == Decimal("45")

    def test_seconds_with_ms(self):
        """Test parsing seconds with milliseconds (no colons)."""
        assert parse_timecode("45.5") == Decimal("45.5")

    def test_invalid_format_raises(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError):
            parse_timecode("invalid")

        with pytest.raises(ValueError):
            parse_timecode("1:2:3:4")

        with pytest.raises(ValueError):
            parse_timecode("")

    def test_invalid_minutes_range(self):
        """Test that minutes >= 60 raises ValueError."""
        with pytest.raises(ValueError, match="Minutes must be less than 60"):
            parse_timecode("1:65:00")

    def test_invalid_seconds_range(self):
        """Test that seconds >= 60 raises ValueError."""
        with pytest.raises(ValueError, match="Seconds must be less than 60"):
            parse_timecode("0:05:75")

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        assert parse_timecode("  1:30:00  ") == Decimal("5400")


class TestFormatTimecode:
    """Tests for format_timecode function."""

    def test_format_with_hours(self):
        """Test formatting with hours."""
        assert format_timecode(Decimal("5025.678")) == "1:23:45.678"

    def test_format_without_hours(self):
        """Test formatting without hours shows 0:MM:SS."""
        assert format_timecode(Decimal("330.5")) == "0:05:30.500"

    def test_format_zero(self):
        """Test formatting zero."""
        assert format_timecode(Decimal("0")) == "0:00:00.000"

    def test_format_no_precision(self):
        """Test formatting with precision=0."""
        assert format_timecode(Decimal("5025.678"), precision=0) == "1:23:45"

    def test_format_single_precision(self):
        """Test formatting with precision=1."""
        assert format_timecode(Decimal("5025.678"), precision=1) == "1:23:45.6"

    def test_format_float_input(self):
        """Test that float input is accepted."""
        assert format_timecode(330.5) == "0:05:30.500"

    def test_format_int_input(self):
        """Test that int input is accepted."""
        assert format_timecode(60) == "0:01:00.000"

    def test_format_negative_raises(self):
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            format_timecode(Decimal("-1"))


class TestParseDuration:
    """Tests for parse_duration function."""

    def test_parse_decimal(self):
        """Test parsing Decimal passthrough."""
        d = Decimal("123.456")
        assert parse_duration(d) is d

    def test_parse_float(self):
        """Test parsing float."""
        result = parse_duration(123.456)
        assert result == Decimal("123.456")

    def test_parse_int(self):
        """Test parsing int."""
        result = parse_duration(123)
        assert result == Decimal("123")

    def test_parse_numeric_string(self):
        """Test parsing numeric string."""
        result = parse_duration("123.456")
        assert result == Decimal("123.456")

    def test_parse_timecode_string(self):
        """Test parsing timecode string."""
        result = parse_duration("1:30:00")
        assert result == Decimal("5400")

    def test_parse_invalid_raises(self):
        """Test that invalid values raise."""
        with pytest.raises(ValueError):
            parse_duration("not-a-duration")


class TestRoundTrip:
    """Test that parsing and formatting are inverses."""

    @pytest.mark.parametrize("timecode", [
        "0:00:00.000",
        "0:00:01.000",
        "0:01:00.000",
        "1:00:00.000",
        "1:23:45.678",
        "0:05:30.500",
        "12:59:59.999",
    ])
    def test_roundtrip(self, timecode: str):
        """Test that format(parse(tc)) == tc."""
        seconds = parse_timecode(timecode)
        result = format_timecode(seconds)
        assert result == timecode
