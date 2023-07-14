import fitz
import os
from tkinter import Tk, Button, filedialog, Checkbutton, IntVar
from PIL import Image, ImageDraw
import tkinter.messagebox as messagebox
import concurrent.futures
from tqdm import tqdm
import traceback


class PDFExtractor:
    def __init__(self):
        self.failed_files = []
        self.extracted_files = 0
        self.extracted_pages = []

    def process_pdf(self, pdf_path, remove_page_two, output_directory):
        try:
            # Buka file PDF menggunakan PyMuPDF (fitz)
            pdf = fitz.open(pdf_path)

            # Hapus halaman kedua jika opsi remove_page_two dipilih
            if remove_page_two:
                pdf.delete_page(1)

            num_pages = pdf.page_count

            for i, page in tqdm(enumerate(pdf), desc=f"Mengolah {os.path.basename(pdf_path)}"):
                # Dapatkan objek gambar pada halaman
                image_list = page.get_images(full=True)

                # Pisahkan dan simpan setiap gambar yang memenuhi kriteria ukuran
                if len(image_list) >= 4:
                    image = image_list[3]  # Ambil gambar ke-4 dari daftar gambar
                    xref = image[0]  # Objek referensi gambar
                    base_image = pdf.extract_image(xref)

                    # Periksa ukuran gambar
                    width, height = base_image["width"], base_image["height"]
                    if width >= 0 and height >= 0:
                        image_data = base_image["image"]

                        # Temukan teks setelah "Nama:" dan sebelum tanda kurung "("
                        text = page.get_text().replace('\n', '')
                        start_index = text.find("Nama:") + len("Nama:")
                        end_index = text.find("(", start_index)
                        name = text[start_index:end_index].strip()

                        # Temukan teks di halaman
                        text2 = page.get_text().replace('\n', '')
                        text_list = text2.split(',')
                        if len(text_list) >= 5:
                            name2 = text_list[-4].strip().upper()

                            # Temukan nomor KTA dalam teks
                            start_index = text.find("KTA:") + len("KTA:")
                            end_index = text.find("Nama", start_index)
                            kta_number = text[start_index:end_index].strip()

                            image_directory = os.path.join(output_directory, "Foto")
                            os.makedirs(image_directory, exist_ok=True)

                            image_path = os.path.join(image_directory, f"{name2}_{name}_tidak_bundar.png")

                            # Simpan gambar dalam format PNG
                            with open(image_path, "wb") as f:
                                f.write(image_data)

                            # Manipulasi gambar untuk menambahkan sudut melengkung
                            rounded_image_path = os.path.join(image_directory, f"{name2}_{kta_number}_{name}.png")
                            self.add_rounded_corners(image_path, rounded_image_path)

                            # Hapus versi asli gambar
                            os.remove(image_path)

                            # Pisahkan setiap halaman menjadi file PDF baru
                            pdf_directory = os.path.join(output_directory, "KTA")
                            os.makedirs(pdf_directory, exist_ok=True)

                            new_pdf = fitz.open()
                            new_pdf.insert_pdf(pdf, from_page=i, to_page=i)
                            new_pdf_path = os.path.join(pdf_directory, f"{name2}_{kta_number}_{name}.pdf")
                            new_pdf.save(new_pdf_path)
                            new_pdf.close()

                            self.extracted_pages.append(
                                (os.path.basename(new_pdf_path), f"{os.path.basename(pdf_path)} - Halaman {i+1}")
                            )

                # Ekstrak teks dari halaman
                text = page.get_text()
                text_path = os.path.join(output_directory, "semua_teks.txt")
                with open(text_path, "a", encoding="utf-8") as f:
                    f.write(text.replace(" ", "").replace("\n", ""))

                self.extracted_files += 1

            # Tutup file PDF
            pdf.close()

            # Periksa jumlah halaman dan ekstraksi yang berhasil
            if self.extracted_files != num_pages or len(self.extracted_pages) != num_pages:
                self.failed_files.append((pdf_path, f"Jumlah halaman dan ekstraksi tidak sesuai (Halaman: {num_pages})"))

        except Exception as e:
            error_info = traceback.format_exc()  # Dapatkan traceback kesalahan
            self.failed_files.append((pdf_path, f"Kesalahan: {str(e)}\n{error_info}"))

    def separate_photos_and_text_from_pdf(self, pdf_paths, output_directory, remove_page_two):
        # Ekstraksi menggunakan multithreading
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.process_pdf, pdf_path, remove_page_two, output_directory)
                for pdf_path in pdf_paths
            ]

            # Proses hasil secara berurutan
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Tulis file log untuk PDF yang gagal diekstrak
        if self.failed_files:
            log_file_path = os.path.join(output_directory, "file_gagal.txt")
            with open(log_file_path, "w") as f:
                for file_path, error in self.failed_files:
                    f.write(f"File: {file_path}\nError: {error}\n\n")

        # Tulis log halaman yang berhasil diekstrak
        extracted_pages_path = os.path.join(output_directory, "halaman_diekstrak.txt")
        with open(extracted_pages_path, "a") as f:
            for _, page in self.extracted_pages:
                f.write(f"{page}\n")

            # Tambahkan jumlah total halaman yang diekstrak ke dalam halaman_diekstrak.txt
            f.write(f"Total Halaman Diekstrak: {len(self.extracted_pages)}\n")

        # Tulis log jumlah file dan halaman yang berhasil diekstrak
        log_summary = f"Jumlah file PDF diinput: {len(pdf_paths)}\n"
        log_summary += f"Jumlah file PDF yang berhasil diekstrak: {self.extracted_files}\n"
        log_summary += f"Jumlah halaman PDF yang berhasil diekstrak: {len(self.extracted_pages)}"

        log_summary_path = os.path.join(output_directory, "ringkasan_ekstraksi.txt")
        with open(log_summary_path, "w") as f:
            f.write(log_summary)

        # Tampilkan popup sukses
        messagebox.showinfo("Sukses", "Ekstraksi Berhasil")

    def add_rounded_corners(self, input_path, output_path, radius=20):
        # Buka gambar
        image = Image.open(input_path)
        width, height = image.size

        # Buat mask dengan sudut melengkung
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), (width, height)], radius, fill=255)

        # Terapkan mask pada gambar
        result = Image.new("RGBA", (width, height))
        result.paste(image, mask=mask)

        # Simpan gambar dengan sudut melengkung
        result.save(output_path)


def select_pdf():
    # Buka dialog pemilihan file PDF
    root = Tk()
    root.withdraw()
    pdf_paths = filedialog.askopenfilenames(filetypes=[("File PDF", "*.pdf")])
    root.destroy()

    if pdf_paths:
        # Panggil fungsi ekstraksi dengan file PDF yang dipilih
        output_directory = select_output_folder()
        if output_directory:
            remove_page_two = remove_page_two_checkbox.get() == 1
            extractor = PDFExtractor()
            extractor.separate_photos_and_text_from_pdf(list(pdf_paths), output_directory, remove_page_two)


def select_output_folder():
    # Buka dialog pemilihan folder output
    root = Tk()
    root.withdraw()
    output_directory = filedialog.askdirectory()
    root.destroy()

    return output_directory


if __name__ == "__main__":
    # Membuat GUI dengan Tkinter
    root = Tk()
    root.title("Ekstraksi Foto dan Teks dari PDF")
    root.geometry("300x250")

    # Tombol "Pilih PDF"
    select_pdf_button = Button(root, text="Pilih PDF KTA", command=select_pdf)
    select_pdf_button.pack(pady=10)

    # Checkbox "Hapus Halaman Kedua"
    remove_page_two_checkbox = IntVar()
    remove_page_two_checkbox.set(0)  # Set nilai awal checkbox menjadi 0 (tidak dicentang)
    remove_page_two_checkbutton = Checkbutton(root, text="Hapus Halaman Kedua", variable=remove_page_two_checkbox)
    remove_page_two_checkbutton.pack(pady=10)

    root.mainloop()
