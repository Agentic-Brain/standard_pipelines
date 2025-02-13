import os
import csv

# Determine the path to the "data" folder relative to this file.
data_dir = os.path.join(os.path.dirname(__file__), "data")
print("data_dir:", data_dir)

# Delete the processed folder if it exists
processed_dir = os.path.join(data_dir, "processed")
if os.path.exists(processed_dir):
    import shutil
    shutil.rmtree(processed_dir)

os.makedirs(processed_dir)

# Walk through the data directory and its subdirectories
for root, _, files in os.walk(data_dir):
    for file_name in files:
        # Process only CSV files
        if file_name.lower().endswith(".csv"):
            file_path = os.path.join(root, file_name)
            print(f"Processing CSV file: {file_path}")
            with open(file_path, mode="r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                # Iterate through each row in the CSV file
                for row in reader:
                    print("Row:", row["Title"])
                    # Create output file path

                    clean_title = ''.join(c for c in row['Title'] if c.isalnum() or c.isspace()).lower()
                    clean_title = clean_title[:50]  # Limit length to 50 chars

                    output_file = os.path.join(processed_dir, f"{row['id']} - {clean_title}.txt")
                    
                    # Check if file already exists
                    if os.path.exists(output_file):
                        raise ValueError(f"File {output_file} already exists")
                        
                    # Write title and content to file
                    with open(output_file, "w", encoding="utf-8") as f:
                        # Clean up title by removing special characters and limiting length
                        f.write(f"# {row['Title']}\n\n")
                        f.write(row['Content'])

