<div align="center">

# ⚡ Pro Tweak Utility ⚡

<p>
  <img src="https://img.shields.io/badge/Language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Language: Python">
  <img src="https://img.shields.io/badge/GUI-PyWebView-4A148C?style=for-the-badge" alt="GUI: PyWebView">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT">
</p>

A sleek and powerful Windows optimization tool that allows users to apply and revert system tweaks safely through a modern, web-based interface.

<br>

<img src="./screenshots/screenshot.png" alt="Project Screenshot" width="80%">

</div>

<details>
  <summary><strong>Table of Contents</strong></summary>
  <ol>
    <li><a href="#-about-the-project">About The Project</a></li>
    <li><a href="#-core-features">Core Features</a></li>
    <li><a href="#-technologies-used">Technologies Used</a></li>
    <li><a href="#-getting-started">Getting Started</a></li>
    <li><a href="#-project-structure">Project Structure</a></li>
    <li><a href="#-roadmap">Roadmap</a></li>
    <li><a href="#-license">License</a></li>
  </ol>
</details>

---

## 📖 About The Project

I built this project to be a straightforward tweaking utility that doesn't feel like a risky script. The main goal was to ensure every single tweak could be undone. Before applying a change, the tool automatically saves the original setting. If you don't like a tweak, you can simply revert it with one click.

The cool part is that all the tweaks are defined in a simple `tweaks.json` file. This means you can add or modify optimizations yourself without ever needing to touch the application's code.

---

## ✨ Core Features

*   **Apply and Revert Safely:** Every tweak is reversible. The original system setting is backed up before any changes are made.
*   **System Analyzer:** Scans your PC and suggests some common, safe optimizations to improve performance.
*   **Clean, Modern UI:** The interface is built with standard web tech, so it's easy to use and looks good.
*   **Easy to Modify:** All tweaks live in the `tweaks.json` file. Want to add a new registry tweak? Just add a new entry to the JSON.
*   **Lightweight:** It uses `pywebview` to wrap the web UI, keeping the application small and simple.

---

## 🛠️ Technologies Used

*   **Python 3**
*   **PyWebView** (for the GUI wrapper)
*   **HTML5, CSS3, JavaScript** (for the user interface)

---

## 🚀 Getting Started

Here's how to get the tool running on your machine.

### Prerequisites

*   You need Python 3.8 or newer.
*   This is a Windows-only application.

### Installation & Usage

1.  **Clone the repo:**
    ```sh
    git clone https://github.com/RylieHolmes/Pro-Tweak-Utility.git
    ```
2.  **Go to the project folder:**
    ```sh
    cd Pro-Tweak-Utility
    ```
3.  **Install requirements:**
    ```sh
    pip install pywebview
    ```
4.  **Run the app:**
    You have to run it as an Administrator for it to work.
    ```sh
    python app.py
    ```

---

## 📂 Project Structure

The project is split into two main parts: the Python backend and the web-based frontend.

*   `app.py`: The core Python file. It handles all the logic for applying and reverting tweaks, reading the JSON file, and managing the window itself.
*   `tweaks.json`: This file contains all the tweak definitions. You can edit this to add, remove, or change tweaks.
*   `web/`: This folder holds all the frontend files (`index.html`, `style.css`, and `script.js`).

---

## 🗺️ Roadmap

Here are some ideas for future updates:

*   [ ] Implement the "Game Mode" feature.
*   [ ] Allow users to create and save their own tweak profiles.
*   [ ] Add more tweaks to the default `tweaks.json`.
*   [ ] Create a logging system for better troubleshooting.

---

## 📄 License

This project is distributed under the MIT License. See `LICENSE` for more information.
