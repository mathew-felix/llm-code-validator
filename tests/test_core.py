from llm_code_validator.core import check_source
from llm_code_validator.core import check_paths


def test_detects_openai_chatcompletion_create():
    result = check_source(
        "import openai\nopenai.ChatCompletion.create(model='gpt-4o-mini', messages=[])\n",
        "sample.py",
    )

    assert result.checked_files == 1
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "LCV001"
    assert diagnostic.path == "sample.py"
    assert diagnostic.line == 2
    assert diagnostic.library == "openai"
    assert "ChatCompletion.create" in diagnostic.symbol


def test_detects_openai_chatcompletion_create_with_import_alias():
    result = check_source(
        "import openai as ai\nai.ChatCompletion.create(model='gpt-4o-mini', messages=[])\n",
        "sample.py",
    )

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].symbol == "openai.ChatCompletion.create"


def test_does_not_confuse_current_openai_client_create_methods_with_old_chatcompletion():
    result = check_source(
        "from openai import AsyncOpenAI\nclient = AsyncOpenAI()\nclient.audio.transcriptions.create(model='whisper-1', file=audio_file)\n",
        "sample.py",
    )

    assert result.diagnostics == []


def test_detects_anthropic_old_completions_client_method():
    result = check_source(
        "from anthropic import Anthropic\nclient = Anthropic()\nclient.completions.create(model='claude-2')\n",
        "sample.py",
    )

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].symbol == "anthropic.Anthropic.completions.create"


def test_detects_chromadb_settings_removed_keyword():
    result = check_source(
        "from chromadb.config import Settings\nsettings = Settings(chroma_db_impl='duckdb+parquet')\n",
        "sample.py",
    )

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].library == "chromadb"
    assert result.diagnostics[0].symbol == "Settings"


def test_does_not_flag_chromadb_settings_without_removed_keyword():
    result = check_source(
        "from chromadb.config import Settings\nsettings = Settings(anonymized_telemetry=False)\n",
        "sample.py",
    )

    assert result.diagnostics == []


def test_detects_pandas_alias_object_method():
    result = check_source("import pandas as pd\ndf = pd.DataFrame()\ndf.append({})\n", "sample.py")

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].library == "pandas"
    assert result.diagnostics[0].symbol == "DataFrame.append"


def test_reports_syntax_error_as_diagnostic():
    result = check_source("def broken(:\n", "bad.py")

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "LCV900"


def test_check_paths_scans_directory(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("import pinecone\npinecone.init(api_key='x')\n", encoding="utf-8")

    result = check_paths([str(tmp_path)])

    assert result.checked_files == 1
    assert len(result.diagnostics) == 1


def test_check_paths_ignores_non_python_files(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("import pinecone\npinecone.init(api_key='x')\n", encoding="utf-8")

    result = check_paths([str(tmp_path)])

    assert result.checked_files == 0
    assert result.diagnostics == []


def test_check_paths_tolerates_non_utf8_python_file(tmp_path):
    path = tmp_path / "sample.py"
    path.write_bytes(b"# bad byte: \xb1\nprint('ok')\n")

    result = check_paths([str(tmp_path)])

    assert result.checked_files == 1


def test_check_paths_ignores_virtualenv_site_packages(tmp_path):
    vendored = tmp_path / "userenv" / "Lib" / "site-packages" / "pkg"
    vendored.mkdir(parents=True)
    (vendored / "bad.py").write_text("import openai\nopenai.ChatCompletion.create()\n", encoding="utf-8")
    app = tmp_path / "app.py"
    app.write_text("print('ok')\n", encoding="utf-8")

    result = check_paths([str(tmp_path)])

    assert result.checked_files == 1
    assert result.diagnostics == []


def test_detects_from_import_moved_symbol():
    result = check_source("from langchain.chat_models import ChatOpenAI\n", "sample.py")

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].library == "langchain"


def test_langchain_memory_safe_fix_rule_only_flags_import_line():
    result = check_source(
        "from langchain.memory import ConversationBufferMemory\nmemory = ConversationBufferMemory()\n",
        "sample.py",
    )

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].symbol == "ConversationBufferMemory"
    assert result.diagnostics[0].line == 1


def test_warns_for_dunder_dynamic_import():
    result = check_source("__import__('openai')\n", "sample.py")

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "LCV910"
    assert result.diagnostics[0].confidence == 0.6


def test_warns_for_importlib_dynamic_import():
    result = check_source("import importlib\nimportlib.import_module('openai')\n", "sample.py")

    assert any(diagnostic.code == "LCV910" for diagnostic in result.diagnostics)


def test_detects_direct_stale_call_inside_wrapper_function():
    result = check_source(
        "import openai\n\ndef call_model():\n    return openai.ChatCompletion.create()\n",
        "sample.py",
    )

    assert any(diagnostic.symbol == "openai.ChatCompletion.create" for diagnostic in result.diagnostics)


def test_suppresses_low_confidence_helper_return_by_default():
    result = check_source(
        "import pandas as pd\n\ndef make_df():\n    return pd.DataFrame()\n\ndf = make_df()\ndf.append({})\n",
        "sample.py",
    )

    assert not any(diagnostic.symbol == "DataFrame.append" for diagnostic in result.diagnostics)


def test_can_show_low_confidence_helper_return_diagnostic():
    result = check_source(
        "import pandas as pd\n\ndef make_df():\n    return pd.DataFrame()\n\ndf = make_df()\ndf.append({})\n",
        "sample.py",
        show_low_confidence=True,
    )

    diagnostic = next(diagnostic for diagnostic in result.diagnostics if diagnostic.symbol == "DataFrame.append")
    assert diagnostic.confidence == 0.75


def test_scans_ai_rag_fixture_project():
    result = check_paths(["tests/fixtures/ai_rag_app"])
    symbols = {diagnostic.symbol for diagnostic in result.diagnostics}

    assert "openai.ChatCompletion.create" in symbols
    assert "pinecone.init" in symbols
    assert "ChatOpenAI" in symbols
    assert "GPTSimpleVectorIndex" in symbols
    assert "Client" in symbols
    assert "validator" in symbols


def test_detects_old_langgraph_memorysaver_import():
    result = check_source("from langgraph.checkpoint import MemorySaver\n", "sample.py")

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].library == "langgraph"
    assert result.diagnostics[0].symbol == "langgraph.checkpoint.MemorySaver"


def test_does_not_flag_langgraph_compile_without_old_memorysaver_import():
    result = check_source(
        "from langgraph.graph import StateGraph\n\ngraph = StateGraph(dict)\napp = graph.compile()\n",
        "sample.py",
    )

    assert result.diagnostics == []


def test_does_not_flag_current_langgraph_memorysaver_import():
    result = check_source("from langgraph.checkpoint.memory import MemorySaver\n", "sample.py")

    assert result.diagnostics == []
