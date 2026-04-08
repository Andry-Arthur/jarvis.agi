"""CLI entry point — `python -m jarvis` or `jarvis` after `pip install -e .`

Usage:
  python -m jarvis            # Interactive voice loop
  python -m jarvis chat       # Text-only chat REPL
  python -m jarvis serve      # Start the FastAPI server
  python -m jarvis plan       # Multi-step planning mode
  python -m jarvis index      # Index knowledge base documents
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

load_dotenv()
console = Console()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("jarvis").setLevel(logging.INFO)


def _build_agent():
    from jarvis.core.agent import Agent
    from jarvis.core.memory import Memory
    from jarvis.core.scheduler import CancelReminderTool, ListRemindersTool, ReminderTool, TaskScheduler
    from jarvis.core.tools import ToolRegistry
    from jarvis.llm.router import LLMRouter
    from jarvis.plugins.loader import PluginLoader

    router = LLMRouter.from_env()
    registry = ToolRegistry()

    # Load all integrations
    _load_integrations(registry)

    # Scheduler
    scheduler = TaskScheduler()
    scheduler.start()

    def _notify(msg: str):
        console.print(f"\n[bold yellow]⏰ REMINDER:[/bold yellow] {msg}")

    registry.register_many(
        [
            ReminderTool(scheduler, notify_callback=_notify),
            ListRemindersTool(scheduler),
            CancelReminderTool(scheduler),
        ]
    )

    # Load user plugins
    plugin_loader = PluginLoader()
    n_tools = plugin_loader.load_all(registry)
    if n_tools:
        console.print(f"[dim]Loaded {n_tools} tool(s) from plugins.[/dim]")

    memory = Memory()
    return Agent(llm_router=router, tool_registry=registry, memory=memory)


def _load_integrations(registry) -> None:
    """Load all configured integrations into the tool registry."""
    from jarvis.integrations.browser import BrowserIntegration
    from jarvis.integrations.code_exec import CodeExecIntegration
    from jarvis.integrations.computer_control import ComputerControlIntegration
    from jarvis.integrations.discord_int import DiscordIntegration
    from jarvis.integrations.filesystem import FilesystemIntegration
    from jarvis.integrations.finance import FinanceIntegration
    from jarvis.integrations.github_int import GitHubIntegration
    from jarvis.integrations.gmail import GmailIntegration
    from jarvis.integrations.google_calendar import GoogleCalendarIntegration
    from jarvis.integrations.google_drive import GoogleDriveIntegration
    from jarvis.integrations.home_assistant import HomeAssistantIntegration
    from jarvis.integrations.instagram import InstagramIntegration
    from jarvis.integrations.knowledge_base import KnowledgeBaseIntegration
    from jarvis.integrations.news import NewsIntegration
    from jarvis.integrations.notion import NotionIntegration
    from jarvis.integrations.screen import ScreenIntegration
    from jarvis.integrations.slack import SlackIntegration
    from jarvis.integrations.spotify import SpotifyIntegration
    from jarvis.integrations.telegram import TelegramIntegration
    from jarvis.integrations.weather import WeatherIntegration
    from jarvis.integrations.whatsapp import WhatsAppIntegration
    from jarvis.integrations.youtube import YouTubeIntegration

    integrations = [
        GmailIntegration(), DiscordIntegration(), YouTubeIntegration(), InstagramIntegration(),
        GoogleCalendarIntegration(), GoogleDriveIntegration(), WhatsAppIntegration(),
        TelegramIntegration(), SpotifyIntegration(), SlackIntegration(),
        BrowserIntegration(), FilesystemIntegration(), CodeExecIntegration(),
        ScreenIntegration(), ComputerControlIntegration(), KnowledgeBaseIntegration(),
        WeatherIntegration(), NewsIntegration(), NotionIntegration(),
        GitHubIntegration(), HomeAssistantIntegration(), FinanceIntegration(),
    ]
    for integration in integrations:
        if integration.is_configured():
            registry.register_many(integration.get_tools())
            logging.getLogger("jarvis").debug("Loaded: %s", integration.name)


# ── Voice loop ────────────────────────────────────────────────────────────────


async def voice_loop(agent) -> None:
    from jarvis.voice.stt import SpeechToText
    from jarvis.voice.tts import TextToSpeech
    from jarvis.voice.wake_word import WakeWordDetector

    wake_model = os.getenv("WAKE_WORD_MODEL", "")
    stt = SpeechToText(
        model_size=os.getenv("WHISPER_MODEL", "base"),
        device="cpu",
        compute_type="int8",
    )
    tts = TextToSpeech(voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"))
    detector = WakeWordDetector(model_path=wake_model)

    console.print("[dim]Loading speech recognition model…[/dim]")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, stt._load)

    console.print(
        Panel.fit(
            "[bold cyan]JARVIS.AGI[/bold cyan] — Voice Mode\n"
            "Say [bold]'Hey Jarvis'[/bold] to activate, [bold]Ctrl+C[/bold] to quit.",
            border_style="cyan",
        )
    )

    history: list[dict] = []

    async for _ in detector.listen_forever():
        console.print("[green]✓ Wake word detected![/green] Speak now…")
        await tts.speak("Yes?")

        text = await stt.record_and_transcribe()
        if not text.strip():
            await tts.speak("I didn't catch that. Please try again.")
            continue

        console.print(f"[bold]You:[/bold] {text}")
        console.print("[dim]Thinking…[/dim]")

        # Stream the reply token-by-token in the console
        reply_parts = []
        async for event in agent.stream(text, history=history):
            if event.kind == "chunk":
                chunk = event.data.get("delta", "")
                reply_parts.append(chunk)
                console.print(chunk, end="", markup=False)
            elif event.kind == "tool_call":
                console.print(f"\n[dim]→ {event.data['name']}({event.data['args']})[/dim]")
            elif event.kind == "done":
                if not reply_parts:
                    reply_parts.append(event.data.get("content", ""))

        reply = "".join(reply_parts).strip()
        console.print()  # newline after streaming

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 40:
            history = history[-40:]

        await tts.speak(reply)
        console.print("[dim]Listening for wake word…[/dim]")


# ── Text chat REPL ────────────────────────────────────────────────────────────


async def chat_loop(agent) -> None:
    console.print(
        Panel.fit(
            "[bold cyan]JARVIS.AGI[/bold cyan] — Chat Mode\n"
            "Type your message and press Enter. Type [bold]exit[/bold] to quit.",
            border_style="cyan",
        )
    )

    history: list[dict] = []

    while True:
        try:
            user_input = Prompt.ask("[bold yellow]You[/bold yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if user_input.lower() in ("exit", "quit", "bye"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if not user_input.strip():
            continue

        # Stream tokens in real-time
        console.print("[bold cyan]JARVIS:[/bold cyan] ", end="")
        reply_parts = []
        async for event in agent.stream(user_input, history=history):
            if event.kind == "chunk":
                chunk = event.data.get("delta", "")
                reply_parts.append(chunk)
                console.print(chunk, end="", markup=False)
            elif event.kind == "tool_call":
                console.print(
                    f"\n[dim]→ calling {event.data['name']}…[/dim]",
                    end=""
                )
            elif event.kind == "done" and not reply_parts:
                reply_parts.append(event.data.get("content", ""))
                console.print(reply_parts[-1], end="", markup=False)

        console.print()
        reply = "".join(reply_parts).strip()

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 40:
            history = history[-40:]


# ── Plan mode ─────────────────────────────────────────────────────────────────


async def plan_loop(agent) -> None:
    from jarvis.core.planner import Planner

    planner = Planner(agent=agent)
    console.print(
        Panel.fit(
            "[bold cyan]JARVIS.AGI[/bold cyan] — Plan Mode\n"
            "Describe a complex goal and JARVIS will break it into steps and execute them.",
            border_style="cyan",
        )
    )

    while True:
        try:
            goal = Prompt.ask("[bold yellow]Goal[/bold yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if goal.lower() in ("exit", "quit"):
            break
        if not goal.strip():
            continue

        async for event in planner.execute(goal):
            if event["type"] == "plan_created":
                console.print(f"\n[bold]Plan:[/bold] {event['plan']} ({event['steps']} steps)")
            elif event["type"] == "step_start":
                console.print(f"  [dim]Step {event['step_id']}:[/dim] {event['description']}")
            elif event["type"] == "step_done":
                console.print(f"  [green]✓[/green] {event['result'][:100]}")
            elif event["type"] == "step_failed":
                console.print(f"  [red]✗[/red] {event['error']}")
            elif event["type"] == "plan_done":
                console.print(Panel(Markdown(event["summary"]), title="[cyan]Result[/cyan]", border_style="cyan"))


# ── CLI commands ──────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """JARVIS.AGI — your free, self-hosted AI agent."""
    if ctx.invoked_subcommand is None:
        agent = _build_agent()
        try:
            asyncio.run(voice_loop(agent))
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye.[/dim]")


@main.command()
def chat() -> None:
    """Start an interactive text chat session."""
    agent = _build_agent()
    try:
        asyncio.run(chat_loop(agent))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye.[/dim]")


@main.command()
def plan() -> None:
    """Multi-step autonomous planning mode."""
    agent = _build_agent()
    try:
        asyncio.run(plan_loop(agent))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye.[/dim]")


@main.command()
@click.argument("path", default=".jarvis/knowledge")
def index(path: str) -> None:
    """Index documents into the personal knowledge base."""
    from jarvis.integrations.knowledge_base import KbIndexTool

    async def _run():
        tool = KbIndexTool()
        result = await tool.execute(path=path)
        console.print(result)

    asyncio.run(_run())


@main.command()
@click.option("--host", default=None, help="Bind host (overrides .env API_HOST)")
@click.option("--port", default=None, type=int, help="Bind port (overrides .env API_PORT)")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (dev mode)")
def serve(host: str | None, port: int | None, reload: bool) -> None:
    """Start the JARVIS.AGI API + WebSocket server."""
    import uvicorn

    _host = host or os.getenv("API_HOST", "0.0.0.0")
    _port = port or int(os.getenv("API_PORT", "8000"))

    console.print(
        Panel.fit(
            f"[bold cyan]JARVIS.AGI[/bold cyan] API\n"
            f"Listening on [bold]http://{_host}:{_port}[/bold]\n"
            f"WebSocket: [bold]ws://{_host}:{_port}/ws[/bold]",
            border_style="cyan",
        )
    )

    uvicorn.run(
        "jarvis.api.main:create_app",
        host=_host,
        port=_port,
        reload=reload,
        factory=True,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
