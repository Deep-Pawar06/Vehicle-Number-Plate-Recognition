🚗 Vehicle Number Plate Recognition System

A Python-based vehicle number plate recognition system using OpenCV, EasyOCR, and Tkinter for college gate security and vehicle monitoring.

📌 Project Overview

The Vehicle Number Plate Recognition System is a desktop application designed to identify vehicle registration numbers from images and webcam video. It uses Optical Character Recognition (OCR) to extract plate numbers and compares them with a locally maintained list of authorized vehicles.

The application provides a graphical user interface (GUI) for scanning vehicles, viewing scan statistics, reviewing scan history, and managing vehicle records.

✨ Features

- Number Plate Recognition: Extract vehicle registration numbers using EasyOCR.
- Image Processing: Process images using OpenCV.
- Live Webcam Detection: Capture and process vehicle images through a webcam.
- Dashboard: View total scans, authorized matches, and vehicles not found in the local list.
- Scan History: Review previously recorded vehicle scans.
- Search & Filter History: Find scan records using available search and filter options.
- CSV Data Management: Maintain authorized vehicle records and scan logs.
- CSV Export: Export scan records for reporting and analysis.
- Vehicle Owner Details: Display locally stored owner information when available.
- Dark & Light Themes: Switch between themes for improved usability.
- Desktop GUI: Interact with the application through a Python Tkinter interface.

Note: Features should be documented as available only when they are implemented and tested in the current version of the code.

🛠️ Technologies Used

Technology| Purpose
Python| Core application logic
Tkinter| Desktop graphical user interface
OpenCV| Image processing and webcam access
EasyOCR| Text recognition from number plates
CSV| Authorized vehicle records and scan history
Regular Expressions| Cleaning and validating recognized plate text

📂 Project Structure

Vehicle-Number-Plate-Recognition/

   1) main_gui_updated.py
   2) main.py
   3) authorized_vehicles.csv
   4) scan_log.csv
   5) results/
   6) README.md

- "main_gui_updated.py" — Updated graphical application.
- "main.py" — Original application or core implementation, if retained.
- "authorized_vehicles.csv" — Local list of authorized vehicles.
- "scan_log.csv" — Recorded vehicle scan history.
- "results/" — Directory for generated recognition results, if used.
- "README.md" — Project documentation.

⚙️ Requirements

- Python 3.10 or a compatible Python version
- OpenCV
- EasyOCR
- Tkinter (usually included with standard Windows Python installations)
- A webcam for live detection
- VS Code or another Python editor

🚀 Installation and Setup

1. Clone the repository

git clone https://github.com/Deep-Pawar06/Vehicle-Number-Plate-Recognition.git

2. Open the project directory

cd Vehicle-Number-Plate-Recognition

3. Create a virtual environment (recommended)

python -m venv .venv

Activate it on Windows:

.venv\Scripts\Activate.ps1

4. Install dependencies

python -m pip install opencv-python easyocr

If the project uses additional third-party libraries, install those as well. Tkinter is generally included with Python on Windows.

5. Run the application

For the updated GUI:

python main_gui_updated.py

If you want to run the original version instead, use:

python main.py

Run only the entry-point file that matches the version you intend to use.

First run: EasyOCR may download its model files, so an internet connection may be required initially.

🖥️ Application Modules

1. Dashboard

Displays scan statistics, including total scans, authorized matches, and vehicles not found in the authorized list.

2. Scanner

Processes an image or webcam frame, recognizes the registration number, and checks whether it matches a locally authorized vehicle.

3. Scan History

Displays recorded scans with details such as date, time, plate number, and recognition status. Search, filter, and export options depend on the implemented version.

4. Vehicle Information

Shows owner information associated with a recognized registration number when that information exists in the local records.

5. Theme Settings

Allows the user to switch between dark and light appearance modes.

📄 CSV File Format

"authorized_vehicles.csv"

Example structure:

plate_number,owner_name,vehicle_type
MH12AB1234,Sample Owner,Car
MH14CD5678,Example Owner,Bike

The column names must match the fields expected by your Python code. Owner information is illustrative sample data.

"scan_log.csv"

Example structure:

date_time,plate_number,status,ocr_confidence
2026-10-18 10:30:00,MH12AB1234,AUTHORIZED,0.95
2026-10-18 10:32:00,MH14CD5678,NOT IN LOCAL LIST,0.87

Use the exact column names and formats expected by the application. The confidence values above are examples, not actual test results.

🔄 How It Works

1. The user selects an image or starts webcam scanning.
2. OpenCV reads the image or video frame.
3. EasyOCR detects and extracts text from the number plate.
4. The recognized text is cleaned and checked against the expected registration format.
5. The application compares the plate number with "authorized_vehicles.csv".
6. The result is displayed as an authorized match or a vehicle not found in the local list.
7. The scan is recorded in "scan_log.csv", when logging is enabled.

🎯 Applications

- College gate vehicle monitoring
- Campus parking management
- Local vehicle entry-record systems
- Educational computer vision projects
- Demonstrations of OCR and image processing

🔮 Future Enhancements

- Database integration using MySQL or SQLite
- Automatic gate-control integration with appropriate hardware
- Improved recognition under different lighting conditions
- User login and role-based access
- Advanced reporting and analytics
- Better recognition of difficult plate images
- Secure handling of vehicle and owner information

⚠️ Limitations

- Recognition accuracy depends on image quality, lighting, camera angle, and plate visibility.
- OCR may produce incorrect characters, so results should be verified when necessary.
- A match against the local CSV list confirms only a local record match; it does not independently verify legal authorization or ownership.
- The application is a prototype and should not be treated as a complete access-control or law-enforcement system.

🔐 Privacy and Responsible Use

Use this project only with appropriate permission. Vehicle registration numbers, scan logs, and owner information may be sensitive. Avoid uploading real personal information, private scan histories, or sensitive images to a public repository. Use sample data for demonstrations and follow applicable privacy and data-protection requirements.

👨‍💻 Developer

Deep Pawar
Computer Engineering Student

GitHub: "@Deep-Pawar06" (https://github.com/Deep-Pawar06)

Project Repository: "Vehicle-Number-Plate-Recognition" (https://github.com/Deep-Pawar06/Vehicle-Number-Plate-Recognition)

📜 License

This project is intended for educational and demonstration purposes. Add a suitable open-source license, such as the MIT License, only after deciding the terms under which you want others to use and modify your code.
