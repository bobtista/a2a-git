# A2A Git Agent

An A2A-compliant agent that uses Claude and the Git MCP server to handle git operations through natural language. The agent can perform operations like creating branches, staging changes, committing, and viewing status through simple text commands.

## Prerequisites

- Python 3.11 or higher
- [UV](https://docs.astral.sh/uv/)
- Anthropic API Key (for Claude)
- Git installed

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/a2a-git.git
   cd a2a-git
   ```

2. Create an environment file with your API key:

   ```bash
   echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
   ```

## Running the Agent

### Using UV directly:

```bash
uv run .
```

### Using Docker:

```bash
# Build the image
docker build -t a2a-git .

# Run the container
docker run -p 8052:8052 \
  -v $(pwd):/workspace \
  -e ANTHROPIC_API_KEY=your_api_key_here \
  a2a-git
```

The agent will start on `http://localhost:8052` by default.

## Usage

You can interact with the agent using any A2A-compatible client. Here are some example commands:

```bash
# Using the A2A CLI client
a2a-cli --agent http://localhost:8052

# Example commands:
"Create a new branch called feature/auth"
"Stage all changes and commit with message 'Update docs'"
"Show me the current git status"
"What changes are staged for commit?"
```

## Configuration Options

The agent supports several configuration options:

```bash
python -m git_agent --help

Options:
  --host TEXT    Host to bind the server to (default: localhost)
  --port INTEGER Port to run the server on (default: 8052)
  --repo TEXT    Path to the git repository to manage (default: current directory)
  --help         Show this message and exit
```

## Features

- Natural language git operations
- Streaming support for long-running operations
- Session management for context-aware interactions
- Docker support with workspace mounting

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
