import fitz
import os

def separate_pages_from_pdf(pdf_path, output_directory):
    # Membuat direktori output jika belum ada
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Membuka file PDF menggunakan PyMuPDF (fitz)
    pdf = fitz.open(pdf_path)

    # Memisahkan setiap halaman PDF
    for i in range(len(pdf)):
        page = pdf[i]

        # Menyimpan halaman dalam file terpisah
        page_path = os.path.join(output_directory, f"page_{i+1}.pdf")
        page.export(page_path)

        # Memisahkan foto dan teks dari halaman
        separate_photos_and_text_from_page(page, output_directory, i+1)

    # Menutup file PDF
    pdf.close()

def separate_photos_and_text_from_page(page, output_directory, page_number):
    # Mendapatkan objek gambar pada halaman
    image_list = page.get_images(full=True)

    # Memisahkan setiap gambar dan menyimpannya jika memenuhi kriteria ukuran
    for index, img in enumerate(image_list):
        xref = img[0]  # Referensi objek gambar
        base_image = page.extract_image(xref)

        # Memeriksa ukuran gambar
        width, height = base_image["width"], base_image["height"]
        if width >= 200 and height >= 200 and not (width == 411 and height == 257):
            image = base_image["image"]
            # Mencari teks sesudah "Nama:" dan sebelum tanda kurung "("
            text = page.get_text().replace('\n', '')
            start_index = text.find("Nama:") + len("Nama:")
            end_index = text.find("(", start_index)
            name = text[start_index:end_index].strip()

            image_path = os.path.join(output_directory, f"KTA_{name}_page_{page_number}_image_{index+1}.jpg")

            # Menyimpan gambar dalam format JPEG
            with open(image_path, "wb") as f:
                f.write(image)

    # Memisahkan teks dari halaman
    text = page.get_text()
    text_path = os.path.join(output_directory, f"KTA_page_{page_number}_text.txt")
    with open(text_path, "a", encoding="utf-8") as f:
        f.write(text.replace(" ", "").replace("\n", ""))

# Contoh penggunaan
pdf_path = "kta.pdf"
output_directory = "output_pages"
separate_pages_from_pdf(pdf_path, output_directory)
