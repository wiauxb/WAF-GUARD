import time

class Timer:
    def __init__(self, name="Operation"):
        self.name = name

    def __enter__(self):
        self.start()
        return self

    def start(self):
        self.start_time = time.perf_counter()
        return self.start_time

    def time(self):
        mid = time.perf_counter()
        return mid - self.start_time

    def __exit__(self, exc_type, exc_value, traceback):
        self.end = time.perf_counter()
        self.elapsed = self.end - self.start_time
        print(f"\033[92m⏱️ > {self.name} completed in {f"{self.elapsed//60:.0f}m" if self.elapsed >= 60 else ""}{self.elapsed%60:02.2f}s.\033[0m")
