from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Type


LifecycleCallable = Callable[..., Any]


@dataclass(frozen=True)
class LifecycleDispatch:
    initialize: LifecycleCallable
    build_ui: LifecycleCallable
    store_current_state: LifecycleCallable
    load_index: LifecycleCallable
    save_project_session: LifecycleCallable
    restore_project_session: LifecycleCallable
    handle_export_event: LifecycleCallable


FACADE_METHODS = (
    "__init__",
    "_build_ui",
    "_store_current_state",
    "load_index",
    "_save_project_session_now",
    "_restore_project_session",
    "_handle_export_event",
)


def apply_lifecycle_facade(app_class: Type[Any]) -> None:
    """Freeze the fully configured lifecycle behind one stable dispatch layer.

    Older compatibility modules are installed before this function. This final
    facade becomes the only public class-level wrapper for the high-risk
    lifecycle methods, records the exact dispatch targets and prevents later
    feature modules from extending the historical wrapper chain.
    """

    if getattr(app_class, "_lifecycle_facade_applied", False):
        return

    missing = [name for name in FACADE_METHODS if not callable(getattr(app_class, name, None))]
    if missing:
        raise RuntimeError(f"生命周期收口前缺少方法：{', '.join(missing)}")

    dispatch = LifecycleDispatch(
        initialize=app_class.__init__,
        build_ui=app_class._build_ui,
        store_current_state=app_class._store_current_state,
        load_index=app_class.load_index,
        save_project_session=app_class._save_project_session_now,
        restore_project_session=app_class._restore_project_session,
        handle_export_event=app_class._handle_export_event,
    )

    def initialize(self: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch.initialize(self, *args, **kwargs)

    def build_ui(self: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch.build_ui(self, *args, **kwargs)

    def store_current_state(self: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch.store_current_state(self, *args, **kwargs)

    def load_index(self: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch.load_index(self, *args, **kwargs)

    def save_project_session(self: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch.save_project_session(self, *args, **kwargs)

    def restore_project_session(self: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch.restore_project_session(self, *args, **kwargs)

    def handle_export_event(self: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch.handle_export_event(self, *args, **kwargs)

    initialize.__name__ = "__init__"
    build_ui.__name__ = "_build_ui"
    store_current_state.__name__ = "_store_current_state"
    load_index.__name__ = "load_index"
    save_project_session.__name__ = "_save_project_session_now"
    restore_project_session.__name__ = "_restore_project_session"
    handle_export_event.__name__ = "_handle_export_event"

    app_class.__init__ = initialize
    app_class._build_ui = build_ui
    app_class._store_current_state = store_current_state
    app_class.load_index = load_index
    app_class._save_project_session_now = save_project_session
    app_class._restore_project_session = restore_project_session
    app_class._handle_export_event = handle_export_event
    app_class._lifecycle_dispatch = dispatch
    app_class._lifecycle_facade_methods = FACADE_METHODS
    app_class._lifecycle_facade_applied = True
