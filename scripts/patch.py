import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_132():
    print("=== PATCH_132: SSL Fix & Requirements Slimming ===")

    # 1. Глобальный фикс SSL для GigaChat
    app_path = ROOT / "app.py"
    if app_path.exists():
        content = app_path.read_text(encoding="utf-8")
        if "SSL_CERT_FILE" not in content:
            ssl_fix = '''
import os
from pathlib import Path
_SSL_CERT = str(Path(__file__).resolve().parent / "static" / "certs" / "gigachat_ca_bundle.pem")
os.environ["SSL_CERT_FILE"] = _SSL_CERT
os.environ["REQUESTS_CA_BUNDLE"] = _SSL_CERT
'''
            content = ssl_fix + content
            app_path.write_text(content, encoding="utf-8")
            print("[+] app.py: добавлен путь к сертификату (фикс GigaChat)")

    # 2. Убираем тяжелые библиотеки из requirements.txt
    req_path = ROOT / "requirements.txt"
    if req_path.exists():
        content = req_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if any(x in line for x in ["torch", "sentence-transformers", "chromadb"]):
                continue
            new_lines.append(line)
        req_path.write_text("\n".join(new_lines), encoding="utf-8")
        print("[+] requirements.txt: удалены torch, sentence-transformers, chromadb")

    # 3. Безопасный импорт chromadb (чтобы код не падал, если библиотеки нет)
    rag_path = ROOT / "services" / "rag.py"
    if rag_path.exists():
        content = rag_path.read_text(encoding="utf-8")
        if "chromadb = None" not in content:
            content = content.replace(
                "import chromadb",
                "try:\n    import chromadb\nexcept ImportError:\n    chromadb = None"
            )
            if "if chromadb is None:" not in content:
                content = content.replace(
                    "    def _try_init_vector_mode(self) -> None:\n        try:\n            if not os.path.isdir(CHROMA_DIR):\n                return",
                    "    def _try_init_vector_mode(self) -> None:\n        try:\n            if chromadb is None:\n                return\n            if not os.path.isdir(CHROMA_DIR):\n                return"
                )
            rag_path.write_text(content, encoding="utf-8")
            print("[+] rag.py: безопасный импорт chromadb")

    # 4. Пропускаем распаковку HF-кэша, если нет sentence-transformers
    boot_path = ROOT / "scripts" / "bootstrap.py"
    if boot_path.exists():
        content = boot_path.read_text(encoding="utf-8")
        if "import sentence_transformers" not in content:
            content = content.replace(
                "def _ensure_hf_cache() -> None:\n    root = Path(__file__).resolve().parents[1]",
                "def _ensure_hf_cache() -> None:\n    try:\n        import sentence_transformers\n    except ImportError:\n        print('[bootstrap] sentence-transformers не установлен -> HF-кэш не нужен')\n        return\n    root = Path(__file__).resolve().parents[1]"
            )
            boot_path.write_text(content, encoding="utf-8")
            print("[+] bootstrap.py: пропуск HF-кэша, если нет sentence-transformers")

    print("\n=== Готово ===")

if __name__ == "__main__":
    apply_patch_132()