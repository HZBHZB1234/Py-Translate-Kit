import threading
import time

from translatekit import TranslationConfig, TranslationRequest, TranslatorBase


class BatchTranslator(TranslatorBase):
    SUPPORTED_LANGUAGES = {"auto": "auto", "en": "en"}
    MIN_REQUEST_INTERVAL = 0

    def __init__(self, config):
        self._active = 0
        self.max_active = 0
        self._active_lock = threading.Lock()
        super().__init__(config)

    def _translate_default(self, text, source_lang, target_lang, **kwargs):
        with self._active_lock:
            self._active += 1
            self.max_active = max(self.max_active, self._active)
        try:
            time.sleep(0.02)
            if text == "fail":
                raise RuntimeError("expected failure")
            return {"value": f"{kwargs.get('prefix', '')}{text}"}
        finally:
            with self._active_lock:
                self._active -= 1

    def _parse_api_response(self, response, **kwargs):
        return response["value"]

    def _calculate_retry_delay(self, attempt, strategy):
        return 0


def make_translator(max_workers=2):
    return BatchTranslator(TranslationConfig(
        source_lang="auto",
        target_lang="en",
        max_workers=max_workers,
    ))


def test_translate_many_preserves_order_and_request_options():
    translator = make_translator(max_workers=3)
    results = translator.translate_many([
        TranslationRequest("one", request_id="1", options={"prefix": "A:"}),
        TranslationRequest("two", request_id="2", options={"prefix": "B:"}),
        TranslationRequest("three", request_id="3", options={"prefix": "C:"}),
    ])

    assert [result.request_id for result in results] == ["1", "2", "3"]
    assert [result.value for result in results] == ["A:one", "B:two", "C:three"]
    assert all(result.succeeded for result in results)
    translator.close()


def test_translate_many_isolates_item_failures():
    translator = make_translator(max_workers=2)
    results = translator.translate_many([
        TranslationRequest("ok"),
        TranslationRequest("fail"),
        TranslationRequest("still-ok"),
    ])

    assert results[0].value == "ok"
    assert results[1].value is None
    assert results[1].error is not None
    assert results[2].value == "still-ok"
    translator.close()


def test_concurrent_batches_share_global_executor_limit():
    translator = make_translator(max_workers=2)
    barrier = threading.Barrier(3)

    def run_batch(prefix):
        barrier.wait()
        translator.translate_many([
            TranslationRequest(f"{prefix}-{index}") for index in range(4)
        ])

    threads = [
        threading.Thread(target=run_batch, args=("a",)),
        threading.Thread(target=run_batch, args=("b",)),
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert translator.max_active == 2
    translator.close()


def test_legacy_list_translation_remains_compatible():
    translator = make_translator(max_workers=2)
    assert translator.translate(["one", "two"]) == ["one", "two"]
    translator.close()


def test_long_text_inside_batch_does_not_nest_executor():
    translator = BatchTranslator(TranslationConfig(
        source_lang="auto",
        target_lang="en",
        max_workers=2,
        text_max_length=5,
    ))

    results = translator.translate_many([
        TranslationRequest("abcdefghijk"),
        TranslationRequest("lmnopqrstuv"),
    ])

    assert all(result.succeeded for result in results)
    translator.close()
