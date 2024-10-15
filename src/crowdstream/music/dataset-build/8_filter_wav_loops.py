import pandas as pd

# Load the CSV file
input_file = 'loops_metadata.csv'  # Replace with your input CSV file path
output_file = 'loops_metadata_wav.csv'  # Replace with your desired output file path

# Read the CSV into a DataFrame
df = pd.read_csv(input_file)

# Filter the DataFrame to include only rows where 'file_name' ends with '.wav'
filtered_df = df[df['file_name'].str.endswith('.wav')]

# Save the filtered DataFrame to a new CSV file
filtered_df.to_csv(output_file, index=False)

print(f"Filtered CSV saved to {output_file}")

