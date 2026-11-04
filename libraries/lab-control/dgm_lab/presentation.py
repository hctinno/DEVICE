"""Neutral product labels; original provenance objects remain unmodified."""
import re


def label(value):
    text = str(value)
    text = re.sub(r'\bHCT(?:\s+CO\.?[,]?\s*(?:LTD\.?)?)?', '시험소 전용', text, flags=re.I)
    text = re.sub(r'\bSamsung(?:\s+Electronics)?\b', '단말 OEM', text, flags=re.I)
    return text.replace('삼성전자', '단말 OEM').replace('삼성', '단말 OEM').replace('에이치시티', '시험소 전용')
