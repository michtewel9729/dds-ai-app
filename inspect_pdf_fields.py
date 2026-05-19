from pypdf import PdfReader

pdf_path = "data/raw_forms/Work History Report 3369.pdf"

reader = PdfReader(pdf_path)

if reader.is_encrypted:
    reader.decrypt("")

fields = reader.get_fields()

print("Total fields found:", len(fields))

with open("field_names.txt", "w") as file:
    file.write(f"Total fields found: {len(fields)}\n\n")

    for field_name in fields.keys():
        file.write(field_name + "\n")

print("Saved field names to field_names.txt")