import sys
import re
from contextlib import contextmanager
from io import StringIO

class StreamlitProcessOutput:
    def __init__(self, container):
        self.container = container
        self.output_text = ""
        self.seen_lines = set()

    def clean_text(self, text):
        # Remove códigos ANSI
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)

        # Oculta logs de debug que poluem saída
        if text.strip().startswith('LiteLLM.Info:') or text.strip().startswith('Provider List:'):
            return None

        return text

    def write(self, text):
        cleaned = self.clean_text(text)
        if cleaned is None:
            return

        lines = cleaned.split('\n')
        new_lines = []
        for line in lines:
            line = line.strip()
            if line and line not in self.seen_lines:
                self.seen_lines.add(line)
                new_lines.append(line)

        if new_lines:
            new_content = '\n'.join(new_lines)
            self.output_text = f"{self.output_text}\n{new_content}" if self.output_text else new_content
            self.container.text(self.output_text)

    def flush(self):
        pass

@contextmanager
def capture_output(container):
    """Captura stdout e redireciona para um container do Streamlit."""
    output_handler = StreamlitProcessOutput(container)
    old_stdout = sys.stdout
    sys.stdout = output_handler
    try:
        yield StringIO()
    finally:
        sys.stdout = old_stdout
