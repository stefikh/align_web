import os
from threading import Thread

from flask import Flask, render_template, request, redirect, url_for, Markup
from flask_sqlalchemy import SQLAlchemy
from os.path import join
import time

from sentence_alignment import sentence_alignment
import simalign
import svgwrite
from nltk.tokenize import word_tokenize

# Тут мы создаём необходимую БД и папку, где у нас будут лужать тексты для обработки
app = Flask(__name__)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(APP_ROOT,
                                                                    "instance\\database.db?check_same_thread=False")
db = SQLAlchemy()
db.init_app(app)

UPLOAD_FOLDER = join(APP_ROOT, 'static\\uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Тут у нас наша БД текстов. Точнее пути до файлов.
class Texts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_in_africaans_path = db.Column(db.String, unique=False, nullable=False)
    file_translated_path = db.Column(db.String, unique=False, nullable=False)
    output_html_path = db.Column(db.String, unique=False, nullable=False)


# А вот эта интересная штука называется Поток. Так как код обработки текстов очень длинный и объёмный, то я выделила его
# вот в такую отдельную штуку. Иначе программа может просто вылетать (этот совет я нашла в нескольких статьях на хабре).
class CustomThread(Thread):
    def __init__(self, file_in_africaans_path, file_translated_path, lang_to):
        self.file_in_africaans_path, self.file_translated_path, self.lang_to = file_in_africaans_path, file_translated_path, lang_to
        Thread.__init__(self)

    def run(self):
        with app.app_context():
            output_path = sentence_alignment(self.file_in_africaans_path, self.file_translated_path, self.lang_to)
            print("Sentence alignment done")
            # сохраняем текст
            text = Texts(file_in_africaans_path=self.file_in_africaans_path,
                         file_translated_path=self.file_translated_path,
                         output_html_path="..\\{}".format(output_path))

            db.session.add(text)
            db.session.commit()
        print("Sentence alignment saved")


@app.route('/')
def index():
    return render_template('index.html')


# Эта штука для того, чтобы пользоваться верхним меню, если мы вдруг захотим перейти на другую страницу.
@app.route('/index')
def index_after_change():
    return render_template('index.html')


@app.route('/sentence_alignment')
def sentence_alignment_page():
    return render_template(
        'sentence_alignment.html'
    )


@app.route('/process', methods=['post'])
def upload_file():
    lang_to = request.form.get('lang_to')
    files = request.files
    file_in_africaans = files['file-in-africaans']
    file_translated = files['file-translated']
    if file_in_africaans.filename != '' and file_translated.filename != '':
        now = str(int(time.time()))
        file_in_africaans_path = "{}\\{}__{}".format(UPLOAD_FOLDER, now, file_in_africaans.filename)
        file_translated_path = "{}\\{}__{}".format(UPLOAD_FOLDER, now, file_translated.filename)
        file_in_africaans.save(file_in_africaans_path)
        file_translated.save(file_translated_path)
        custom_thread = CustomThread(file_in_africaans_path, file_translated_path, lang_to)
        custom_thread.start()

    return redirect(url_for('sentence_alignment_page'))


@app.route('/word_alignment')
def word_page():
    return render_template(
        'word_alignment.html'
    )


@app.route('/process_2', methods=['post', 'get'])
def aling():
    src_sentence = request.form.get('Sentence_afr')
    trg_sentence = request.form.get('Sentence_tr')

    model = simalign.SentenceAligner()
    result = model.get_word_aligns(src_sentence, trg_sentence)

    test = svgwrite.Drawing('test_simalign.svg', profile='tiny')

    sentence = word_tokenize(src_sentence)
    sentence2 = word_tokenize(trg_sentence)

    x1 = 30
    x1_cor = []
    for slovo in sentence:
        test.add(test.text(slovo, insert=(x1, 20), fill='black'))
        x1_cor.append(x1)
        x1 = x1 + len(slovo) * 10 + 10

    x2 = 30
    x2_cor = []
    for slovo in sentence2:
        test.add(test.text(slovo, insert=(x2, 100), fill='black'))
        x2_cor.append(x2)
        x2 = x2 + len(slovo) * 10 + 10

    for para in result['mwmf']:
        test.add(
            test.line(start=(x1_cor[para[0]] + 10, 25), end=(x2_cor[para[1]] + 10, 85), stroke_width="3",
                      stroke="blue"))

    test.save()
    svg = open('test_simalign.svg').read()

    return render_template('align.html', svg=Markup(svg))


@app.route('/uploaded_texts', methods=['get'])
def uploaded_page():
    texts = list(db.session.query(Texts))
    return render_template(
        'uploaded_texts.html', texts=texts
    )


if __name__ == '__main__':
    app.run(debug=True)
