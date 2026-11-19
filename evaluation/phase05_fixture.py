"""Invented textbook/slides/notes: agreement, conditions, direct conflict, missing data."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
from xml.sax.saxutils import escape

TEXTBOOK=[
 'Linear regression is a supervised learning model that predicts a numerical target.',
 'Mean squared error (MSE) measures the average squared prediction error.',
 "Gradient descent requires feature scaling for this course's exercises.",
 'Assignment LAB-A is due on 18 April 2026 for Group A.',
]
SLIDES=[
 'Linear regression predicts a numerical target.',
 'MSE means mean squared error.',
 'Decision trees do not require feature scaling in this course.',
 'Assignment LAB-A is due on 21 April 2026 for Group A.',
 'Gradient descent minimizes mean squared error.',
]
NOTES='''# Ghi chú ôn tập

MSE (mean squared error) là trung bình bình phương sai số dự đoán.

Cần chuẩn hóa đặc trưng khi dùng gradient descent trong bài thực hành.

Quy tắc không cần chuẩn hóa trong slide áp dụng cho cây quyết định, không áp dụng cho gradient descent.
'''
CRITERIA=['Ý nghĩa MSE','Điều kiện chuẩn hóa đặc trưng','Hạn nộp LAB-A cho nhóm A','Chi phí học phần']
GOAL='Đối chiếu các khái niệm, điều kiện áp dụng và thông tin học tập giữa giáo trình, slide và ghi chú.'


def create_fixture(directory):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
 xml+=''.join('<w:p><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p>' for text in TEXTBOOK)+'</w:body></w:document>'
 with ZipFile(directory/'textbook.docx','w',ZIP_DEFLATED) as archive:
  archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
  archive.writestr('word/document.xml',xml)
 from pypdf import PdfWriter
 from pypdf.generic import DecodedStreamObject,DictionaryObject,NameObject
 writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
 font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
 page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
 stream=DecodedStreamObject();stream.set_data(('BT /F1 10 Tf 40 720 Td '+ ' '.join('('+text.replace('(','\\(').replace(')','\\)')+') Tj 0 -25 Td' for text in SLIDES)+' ET').encode())
 page[NameObject('/Contents')]=writer._add_object(stream);writer.write(directory/'slides.pdf')
 (directory/'notes.md').write_text(NOTES,encoding='utf-8')
 return [directory/'textbook.docx',directory/'slides.pdf',directory/'notes.md']
