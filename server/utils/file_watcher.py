import os.path

from tornado.ioloop import IOLoop, PeriodicCallback


class FileWatcher:

    def __init__(self, file_path, callback, poll_interval=500):
        if not os.path.isfile(file_path):
            raise RuntimeError(f'Path {file_path} does not exist')

        self._file_path = file_path
        self._poll_interval = poll_interval
        self._callback = callback
        self._paused = False
        self._last_fs_time = None

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def watch(self):
        raise NotImplementedError

    def update_m_time(self):
        self._last_fs_time = os.path.getmtime(self._file_path)


class IOLoopFileWatcher(FileWatcher):

    def __init__(self, file_path, callback, poll_interval=500):
        if not IOLoop.current():
            raise RuntimeError('No IOLoop found!')

        super().__init__(file_path, callback, poll_interval)
        self._task: PeriodicCallback = PeriodicCallback(self._poll_file, self._poll_interval, 0.05)

    def _poll_file(self):
        current_file_time = os.path.getmtime(self._file_path)
        if current_file_time > self._last_fs_time and not self._paused:
            self._callback()
        self._last_fs_time = current_file_time

    def watch(self):
        self._last_fs_time = os.path.getmtime(self._file_path)
        self._task.start()

    def stop(self):
        self._task.stop()
