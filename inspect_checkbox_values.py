from pypdf import PdfReader

reader = PdfReader("data/raw_forms/Work History Report 3369.pdf")

if reader.is_encrypted:
    reader.decrypt("")

fields = reader.get_fields()

for name in [
    "form1[0].Page4[0].P4-InteractYes-CB[0]",
    "form1[0].Page4[0].P4-InteractNo-CB[0]",
]:
    print("\nFIELD:", name)
    print(fields.get(name))