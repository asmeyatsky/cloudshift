"""Composition root: wires all domain ports to concrete infrastructure adapters.

This is the ONLY module in the codebase that references concrete adapter
implementations.  Every other module depends on the port protocols defined
in ``cloudshift.domain.ports``.
"""

from __future__ import annotations

from cloudshift.infrastructure.config.settings import Settings

# -- Concrete adapter imports (only place these appear) ---------------------
from cloudshift.infrastructure.file_system.local_fs import LocalFileSystem
from cloudshift.infrastructure.llm.null_adapter import NullLLMAdapter
from cloudshift.infrastructure.llm.ollama_adapter import OllamaAdapter
from cloudshift.infrastructure.pattern_store.local_store import LocalPatternStore
from cloudshift.infrastructure.persistence.sqlite_repository import SQLiteProjectRepository
from cloudshift.infrastructure.rust_adapters.detector_adapter import RustDetectorAdapter
from cloudshift.infrastructure.rust_adapters.diff_adapter import RustDiffAdapter
from cloudshift.infrastructure.rust_adapters.parser_adapter import RustParserAdapter
from cloudshift.infrastructure.rust_adapters.pattern_engine_adapter import RustPatternEngineAdapter
from cloudshift.infrastructure.rust_adapters.validation_adapter import RustValidationAdapter
from cloudshift.infrastructure.rust_adapters.walker_adapter import RustWalkerAdapter
from cloudshift.infrastructure.validation.test_runner import SubprocessTestRunner


class Container:
    """Dependency injection container (composition root).

    Instantiates and wires all adapters according to ``Settings``.
    Access individual adapters via properties; instances are created
    lazily and cached for the container's lifetime.

    Usage::

        container = Container()          # uses defaults / env vars
        parser = container.parser        # RustParserAdapter
        llm = container.llm              # Ollama or Null depending on settings
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._instances: dict[str, object] = {}

    @property
    def settings(self) -> Settings:
        return self._settings

    # -- Source-code analysis ports -----------------------------------------

    @property
    def parser(self) -> RustParserAdapter:
        return self._get_or_create("parser", self._make_parser)

    @property
    def detector(self) -> RustDetectorAdapter:
        return self._get_or_create("detector", self._make_detector)

    @property
    def pattern_engine(self) -> RustPatternEngineAdapter:
        return self._get_or_create("pattern_engine", self._make_pattern_engine)

    # -- Diff port ----------------------------------------------------------

    @property
    def diff(self) -> RustDiffAdapter:
        return self._get_or_create("diff", self._make_diff)

    # -- File system ports --------------------------------------------------

    @property
    def walker(self) -> RustWalkerAdapter:
        return self._get_or_create("walker", self._make_walker)

    @property
    def file_system(self) -> LocalFileSystem:
        return self._get_or_create("file_system", self._make_file_system)

    # -- Validation ports ---------------------------------------------------

    @property
    def validation(self) -> RustValidationAdapter:
        return self._get_or_create("validation", self._make_validation)

    @property
    def test_runner(self) -> SubprocessTestRunner:
        return self._get_or_create("test_runner", self._make_test_runner)

    # -- Persistence ports --------------------------------------------------

    @property
    def project_repository(self) -> SQLiteProjectRepository:
        return self._get_or_create("project_repository", self._make_project_repository)

    # -- Pattern store ------------------------------------------------------

    @property
    def pattern_store(self) -> LocalPatternStore:
        return self._get_or_create("pattern_store", self._make_pattern_store)

    # -- LLM port -----------------------------------------------------------

    @property
    def llm(self) -> OllamaAdapter | NullLLMAdapter:
        return self._get_or_create("llm", self._make_llm)

    # -- Factory methods ----------------------------------------------------

    def _make_parser(self) -> RustParserAdapter:
        return RustParserAdapter()

    def _make_detector(self) -> RustDetectorAdapter:
        return RustDetectorAdapter(parser=self.parser)

    def _make_pattern_engine(self) -> RustPatternEngineAdapter:
        engine = RustPatternEngineAdapter(parser=self.parser)
        patterns_dir = self._settings.patterns_dir
        if patterns_dir.is_dir():
            engine.load_patterns(str(patterns_dir))
        return engine

    def _make_diff(self) -> RustDiffAdapter:
        return RustDiffAdapter()

    def _make_walker(self) -> RustWalkerAdapter:
        return RustWalkerAdapter()

    def _make_file_system(self) -> LocalFileSystem:
        return LocalFileSystem()

    def _make_validation(self) -> RustValidationAdapter:
        return RustValidationAdapter(parser=self.parser)

    def _make_test_runner(self) -> SubprocessTestRunner:
        return SubprocessTestRunner()

    def _make_project_repository(self) -> SQLiteProjectRepository:
        return SQLiteProjectRepository(db_path=self._settings.db_path)

    def _make_pattern_store(self) -> LocalPatternStore:
        return LocalPatternStore(directory=self._settings.patterns_dir)

    def _make_llm(self) -> OllamaAdapter | NullLLMAdapter:
        if self._settings.llm_enabled:
            return OllamaAdapter(
                base_url=self._settings.ollama_base_url,
                model=self._settings.ollama_model,
                timeout=self._settings.ollama_timeout,
            )
        return NullLLMAdapter()

    # -- Use case resolution ------------------------------------------------

    def resolve(self, use_case_cls):
        """Instantiate a use case class with the correct adapters."""
        from cloudshift.application.use_cases import (
            ApplyTransformationUseCase,
            GeneratePlanUseCase,
            GenerateReportUseCase,
            ManagePatternsUseCase,
            ScanProjectUseCase,
            ValidateTransformationUseCase,
        )

        factories = {
            ScanProjectUseCase: lambda: ScanProjectUseCase(
                fs=self.file_system,
                parser=self.parser,
                detector=self.detector,
                allowed_paths=self._settings.allowed_scan_paths,
            ),
            GeneratePlanUseCase: lambda: GeneratePlanUseCase(
                pattern_engine=self.pattern_engine,
                manifest_store=self.project_repository,
            ),
            ApplyTransformationUseCase: lambda: ApplyTransformationUseCase(
                plan_store=self.project_repository,
                pattern_engine=self.pattern_engine,
                fs=self.file_system,
                diff_engine=self.diff,
            ),
            ValidateTransformationUseCase: lambda: ValidateTransformationUseCase(
                ast_validator=self.validation,
                residual_scanner=self.validation,
                sdk_checker=self.validation,
                test_runner=self.test_runner,
                transform_store=self.project_repository,
            ),
            ManagePatternsUseCase: lambda: ManagePatternsUseCase(
                pattern_store=self.pattern_store,
            ),
            GenerateReportUseCase: lambda: GenerateReportUseCase(
                project_store=self.project_repository,
                scan_store=self.project_repository,
                transform_store=self.project_repository,
                validation_store=self.project_repository,
            ),
        }

        factory = factories.get(use_case_cls)
        if factory is None:
            raise ValueError(f"Unknown use case: {use_case_cls.__name__}")
        return factory()

    def config(self):
        """Return a config accessor wrapping Settings."""
        return _ConfigAccessor(self._settings)

    # -- Internal helpers ---------------------------------------------------

    def _get_or_create(self, key: str, factory):
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]

    async def close(self) -> None:
        """Shut down resources that hold connections."""
        if "llm" in self._instances:
            llm = self._instances["llm"]
            if hasattr(llm, "close"):
                await llm.close()
        if "project_repository" in self._instances:
            repo = self._instances["project_repository"]
            if hasattr(repo, "close"):
                repo.close()


class _ConfigAccessor:
    """Simple config accessor wrapping Settings for CLI config commands."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, key: str):
        return getattr(self._settings, key, None)

    def set(self, key: str, value: str) -> None:
        if hasattr(self._settings, key):
            field_type = type(getattr(self._settings, key))
            if field_type is bool:
                setattr(self._settings, key, value.lower() in ("true", "1", "yes"))
            elif field_type is int:
                setattr(self._settings, key, int(value))
            elif field_type is float:
                setattr(self._settings, key, float(value))
            else:
                setattr(self._settings, key, value)

    def as_dict(self) -> dict:
        return self._settings.model_dump(mode="json")
