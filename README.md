# FXMacroData Python SDK 🐍📊

![PyPI Version](https://img.shields.io/pypi/v/fxmacrodata?color=blue&logo=python&style=flat-square)
![Python Versions](https://img.shields.io/pypi/pyversions/fxmacrodata?style=flat-square)
![License](https://img.shields.io/github/license/yourusername/fxmacrodata?style=flat-square)
![Build](https://img.shields.io/github/actions/workflow/status/yourusername/fxmacrodata/python-package.yml?style=flat-square&logo=github)

The **FXMacroData Python SDK** is a lightweight, easy-to-use client for fetching **forex macroeconomic data** from [FXMacroData](https://fxmacrodata.com/?utm_source=github&utm_medium=readme&utm_campaign=python_sdk).  

It supports **synchronous** and **asynchronous** requests, provides ready-to-use JSON responses, and enforces API keys only for non-USD endpoints. Perfect for developers, quants, and algo traders.

---

## 🌟 Features

- Fetch **policy rates, CPI, inflation, GDP, unemployment**, and other macroeconomic indicators.
- Supports **USD (free)** and **other currencies via RapidAPI key**.
- **Async-first** design for bulk data fetching.
- Works with **Python 3.9+**.
- Compatible with **TradingBots, Jupyter Notebooks, Backtests**.
- Minimal dependencies: `requests`, `aiohttp`.

---

## 📦 Installation

```bash
pip install fxmacrodata
```

Or install the latest version from GitHub:

```bash
pip install git+https://github.com/yourusername/fxmacrodata.git
```