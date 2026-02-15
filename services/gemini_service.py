import json
import google.generativeai as genai
from PIL import Image
import config


genai.configure(api_key=config.GEMINI_API_KEY)

EXTRACTION_PROMPT = """You are an invoice data extraction assistant. Analyze this invoice image/document and extract the following fields.

Return ONLY a valid JSON object with these exact keys:
{
  "month": "the month of the invoice (e.g. January 2025)",
  "invoice_date": "the invoice date in DD/MM/YYYY format",
  "transaction_type": "type of transaction (e.g. Purchase, Service, Rental, Utility, etc.)",
  "category": "category of the transaction (e.g. Office Supplies, Food & Beverage, Transportation, Utilities, IT Equipment, Marketing, Maintenance, etc.)",
  "supplier": "supplier/vendor name",
  "description": "brief description of items/services",
  "amount": "total amount as a number (no currency symbol)"
}

Rules:
- If a field cannot be determined, use "N/A"
- For amount, extract the grand total / total payable. Return just the number (e.g. 150.00)
- For month, derive from the invoice date
- Be concise in the description, summarize the main items/services
- Return ONLY the JSON, no other text
"""


def extract_invoice_data(file_path: str) -> dict:
    """Extract invoice data from an image or PDF using Gemini."""
    model = genai.GenerativeModel("gemini-2.0-flash")

    if file_path.lower().endswith(".pdf"):
        with open(file_path, "rb") as f:
            pdf_data = f.read()
        response = model.generate_content(
            [
                EXTRACTION_PROMPT,
                {"mime_type": "application/pdf", "data": pdf_data},
            ]
        )
    else:
        image = Image.open(file_path)
        response = model.generate_content([EXTRACTION_PROMPT, image])

    raw = response.text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]  # remove opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # remove closing ```
        raw = "\n".join(lines)

    return json.loads(raw)
