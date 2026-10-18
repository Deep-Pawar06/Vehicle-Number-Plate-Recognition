import cv2
import easyocr
import re
import os
import csv
import numpy as np
from datetime import datetime
from tkinter import Tk, filedialog

print("Loading number plate recognition...")
reader = easyocr.Reader(["en"], gpu=False)
print("System ready!")


def clean_plate(text):
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def main():
    root = Tk()
    root.withdraw()

    image_path = filedialog.askopenfilename(
        title="Select Vehicle Image",
        filetypes=[
            ("Images", "*.jpg *.jpeg *.png *.bmp")
        ]
    )

    root.destroy()

    if not image_path:
        print("No image selected.")
        return

    image = cv2.imread(image_path)

    if image is None:
        print("Could not open image.")
        return

    results = reader.readtext(
        image,
        detail=1,
        paragraph=False,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )

    print("\nOCR Results:")

    for box, text, confidence in results:
        print(
            "Text:", repr(text),
            "| Confidence:", round(confidence, 2)
        )

    authorized = {}

    csv_path = "authorized_vehicles.csv"

    if os.path.exists(csv_path):
        with open(
            csv_path, newline="", encoding="utf-8-sig"
        ) as f:
            for row in csv.DictReader(f):
                plate = clean_plate(
                    row.get("plate_number", "")
                )

                if plate:
                    authorized[plate] = row.get(
                        "owner_name", "Unknown"
                    )
    else:
        print("Warning: authorized_vehicles.csv not found.")

    found = False

    # Basic Indian registration number format
    pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"

    for box, text, confidence in results:
        plate = clean_plate(text)

        if re.fullmatch(pattern, plate) and confidence >= 0.25:
            found = True

            print("\nDetected plate:", plate)
            print("OCR confidence:", round(confidence, 2))

            if plate in authorized:
                status = "AUTHORIZED"
                print("Status: AUTHORIZED")
                print("Registered owner:", authorized[plate])
            else:
                status = "NOT IN LOCAL LIST"
                print("Status: NOT IN LOCAL LIST")

            points = [
                (int(p[0]), int(p[1])) for p in box
            ]

            cv2.polylines(
                image,
                [np.array(points, dtype=np.int32)],
                True,
                (0, 255, 0),
                2
            )

            cv2.putText(
                image,
                plate,
                points[0],
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            log_exists = os.path.exists("scan_log.csv")

            with open(
                "scan_log.csv",
                "a",
                newline="",
                encoding="utf-8"
            ) as f:
                writer = csv.writer(f)

                if not log_exists:
                    writer.writerow(
                        ["date_time", "plate_number", "status"]
                    )

                writer.writerow([
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    plate,
                    status
                ])

    if not found:
        print("No likely plate detected.")
        print("Try a clear, close-up vehicle image.")

    output_dir = "results"
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(
        output_dir, "annotated_result.jpg"
    )

    cv2.imwrite(output_path, image)
    print("Result saved to:", output_path)

    cv2.imshow("Recognition Result", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
    