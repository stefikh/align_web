import os

from lingtrain_aligner import preprocessor, splitter, aligner, resolver, reader
import time


# Подробнее об этом коде можете прочитать в теоретической справке проекта.
def sentence_alignment(file_in_africaans_path, file_translated_path, lang_to):
    with open(file_in_africaans_path, "r", encoding="utf8") as input1:
        text1 = input1.readlines()

    with open(file_translated_path, "r", encoding="utf8") as input2:
        text2 = input2.readlines()

    now = str(int(time.time()))
    db_path = "{}.db".format(now)

    lang_from = "afr"

    model_name = "sentence_transformer_multilingual"

    text1_prepared = preprocessor.mark_paragraphs(text1)
    text2_prepared = preprocessor.mark_paragraphs(text2)

    splitted_from = splitter.split_by_sentences_wrapper(text1_prepared, lang_from)
    splitted_to = splitter.split_by_sentences_wrapper(text2_prepared, lang_to)

    # Создаётся БД для одного текста.
    if os.path.isfile(db_path):
        os.unlink(db_path)

    aligner.fill_db(db_path, lang_from, lang_to, splitted_from, splitted_to)

    batch_ids = [0, 1, 2, 3, 4]

    aligner.align_db(db_path, model_name, batch_size=200, window=40, batch_ids=batch_ids, save_pic=False,
                     embed_batch_size=50, normalize_embeddings=True, show_progress_bar=True)

    steps = 3

    for i in range(steps):
        conflicts, rest = resolver.get_all_conflicts(db_path,
                                                     min_chain_length=2 + i,
                                                     max_conflicts_len=7 * (i + 1),
                                                     batch_id=-1)

        resolver.resolve_all_conflicts(db_path, conflicts, model_name, show_logs=False)

        if len(rest) == 0:
            break

    # Тут собирается сам текст с выделенными предложениями
    output_path = "static/results/{}.html".format(now)
    paragraphs, delimeters, metas, sent_counter = reader.get_paragraphs(
        db_path, direction="to"
    )

    my_style = [
        '{"background": "#A2E4B8", "color": "black", "border-bottom": "0px solid red"}',
        '{"background": "#FFC1CC", "color": "black"}',
        '{"background": "#9BD3DD", "color": "black"}',
        '{"background": "#FFFCC9", "color": "black"}'
    ]

    lang_ordered = ["from", "to"]

    reader.create_book(
        lang_ordered=lang_ordered,
        paragraphs=paragraphs,
        delimeters=delimeters,
        metas=metas,
        sent_counter=sent_counter,
        output_path=output_path,
        template="pastel_fill",
        styles=[my_style],
    )

    return output_path
