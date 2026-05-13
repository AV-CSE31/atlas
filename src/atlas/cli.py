import typer
from .init import init_kb as _init_kb
from .ingest import ingest_cmd as _ingest_cmd
from .diff import diff_cmd as _diff_cmd
from .compile import compile_cmd as _compile_cmd
from .index_cmd import index_cmd as _index_cmd
from .search import search_cmd as _search_cmd
from .qa import lint_cmd as _lint_cmd
from .maintenance import archive_cmd as _archive_cmd
from .server import serve_cmd as _serve_cmd

app = typer.Typer(help="Atlas Knowledge Compiler CLI")

@app.command()
def init():
    """Initialize a new Atlas knowledge base."""
    _init_kb()

@app.command()
def ingest(source: str):
    """Ingest a URL or local file into the raw directory."""
    _ingest_cmd(source)

@app.command()
def diff():
    """Show pending raw files that need compilation."""
    _diff_cmd()

@app.command()
def compile(incremental: bool = True):
    """Compile the knowledge base."""
    _compile_cmd(incremental)

@app.command("index")
def index_wiki():
    """Index compiled wiki articles into the search database."""
    _index_cmd()

@app.command()
def search(query: str):
    """Search the knowledge base."""
    _search_cmd(query)

@app.command()
def lint():
    """Run health checks and consistency validation (QA Agent)."""
    _lint_cmd()

@app.command()
def archive():
    """Run Adaptive Knowledge Lifecycle scoring and archiving (Maintenance Agent)."""
    _archive_cmd()

@app.command()
def serve():
    """Run the MCP server for external integrations."""
    _serve_cmd()

@app.command()
def version():
    """Print the version of Atlas."""
    typer.echo("Atlas Knowledge Compiler v0.1.0")

if __name__ == "__main__":
    app()
