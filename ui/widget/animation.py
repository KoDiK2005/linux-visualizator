"""Лёгкое сглаживание числовых значений для плавных переходов в панелях.

Не привязано к Qt-анимациям, чтобы не тащить лишнюю инфраструктуру: каждая
панель сама вызывает step() из общего таймера в MainWindow и перерисовывается.
"""

SMOOTHING_FACTOR = 0.25  # доля пути к цели за один шаг анимации


class SmoothedValue:
    def __init__(self, initial: float = 0.0) -> None:
        self.value = initial
        self.target = initial

    def set_target(self, target: float) -> None:
        self.target = target

    def step(self) -> bool:
        """Продвигает значение к цели. Возвращает True, если значение ещё меняется."""
        delta = self.target - self.value
        if abs(delta) < 0.05:
            if self.value != self.target:
                self.value = self.target
                return True
            return False
        self.value += delta * SMOOTHING_FACTOR
        return True


class SmoothedList:
    """Список сглаженных значений переменной длины (например, по числу ядер CPU)."""

    def __init__(self) -> None:
        self._items: list[SmoothedValue] = []

    @property
    def values(self) -> list[float]:
        return [item.value for item in self._items]

    def set_targets(self, targets: list[float]) -> None:
        while len(self._items) < len(targets):
            self._items.append(SmoothedValue(targets[len(self._items)]))
        del self._items[len(targets):]
        for item, target in zip(self._items, targets):
            item.set_target(target)

    def step(self) -> bool:
        return any([item.step() for item in self._items])
