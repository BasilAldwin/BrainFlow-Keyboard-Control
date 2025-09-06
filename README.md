## Core Features
Web-Based GUI: Control everything from a clean, modern interface in your web browser. No complex command-line arguments needed.

## Broad Device Support:
Powered by BrainFlow, this application is compatible with dozens of EEG headsets, including Muse, GANN Biomedical, Cyton, and more.

## Selectable Metric Modes:
Choose between two distinct control methods:

## Focus Ratio
Uses a Beta / Alpha wave ratio to measure active concentration.

## Alpha Power
Uses the raw power of the Alpha band to measure relaxed states.

Personalized Calibration
A one-click calibration routine measures your unique baseline brain activity, ensuring the system is responsive and balanced for you.

Real-Time Visualization
A live graph provides immediate feedback on your selected brainwave metric, helping you understand and master the controls.

## Advanced Key Bindings
Assign any single key (w, space) or complex combination (ctrl+alt+delete) to Left/Right hemisphere activation.

## Tunable Smoothing & Sensitivity
Use simple sliders to control the signal smoothing (EMA) and activation thresholds to fine-tune the responsiveness to your liking.

## How It Works
This project uses a simple and robust architecture:

## Python Backend
A lightweight Flask server handles the direct connection to your EEG device using the BrainFlow library. It performs all the signal processing, calculates the metrics, and hosts a WebSocket for real-time communication.

## HTML/JavaScript Frontend
A single, self-contained HTML file provides the user interface. It connects to the Python server's WebSocket to send commands (like "start calibration") and receive a live stream of data to display on the graphs.

## Getting Started
Prerequisites
[Python 3.11.5](https://www.python.org/downloads/release/python-3115/) installed and accessible from your command line.

A BrainFlow-compatible EEG device.

## Installation & Usage
Download the Project: Download all the files from this repository (muse_server_backend.py, install.bat, run.bat, requirements.txt) and place them in a new folder on your computer.

### Install Dependencies
Double-click the install.bat script. This will open a terminal, download, and install all the necessary Python libraries from the requirements.txt file. You only need to do this once.

### Run the Application
Double-click the run.bat script. This will start the Python server, and your default web browser should automatically open to the control interface.

Connect and Calibrate:

Select your EEG device from the dropdown menu.

Click Connect.

Once connected, click Calibrate and relax for 10 seconds while the application measures your baseline brain activity.

## Configure and Control

Choose your desired Metric Mode.

Adjust the Smoothing and Sensitivity sliders.

Set your desired Key Bindings.

You're ready to go! The application will now press your configured keys when your brain activity meets the trigger conditions.

## Acknowledgements
This project was heavily inspired by the architecture and methodologies of the BrainFlowsIntoVRChat project by ChilloutCharles. Many thanks to them for pioneering a robust and flexible approach to BCI with BrainFlow.

This application would not be possible without the incredible, open-source BrainFlow library, which provides a unified and stable API for a vast range of biosensor devices.

License
This project is licensed under the MIT License.

Wrote this with Gemini 2.5 PRO (Ican'tCode.JPG)
