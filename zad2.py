import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class Task(ABC):
    registry = {}
    STATUS = ["pending", "in progress", "done"]

    def __init_subclass__(cls, **kwargs):
        Task.registry[cls.__name__] = cls
        super().__init_subclass__(**kwargs)

    def __init__(self, title, description="", status="pending"):
        self.title = title
        self.description = description
        self.status = status
        self.created = datetime.now()

    def next_status(self):
        i = Task.STATUS.index(self.status)
        if i < len(Task.STATUS) - 1:
            self.status = Task.STATUS[i + 1]

    def __str__(self):
        created_str = self.created.strftime("%Y-%m-%d %H:%M")
        return f"[{self.__class__.__name__}] {self.title} ({self.status}) - utw: {created_str}"

    def __lt__(self, other):
        return self.created < other.created

    def __eq__(self, other):
        return self.title == other.title and self.status == other.status

    def to_dict(self):
        return {
            "task_type": self.__class__.__name__,
            "kwargs": {
                "title": self.title,
                "description": self.description,
                "status": self.status,
                "created": self.created.strftime("%Y-%m-%d %H:%M:%S"),
            }
        }

    @classmethod
    def from_dict(cls, data):
        task_type = data["task_type"]
        if task_type not in Task.registry:
            raise ValueError(f"Unknown task type: {task_type}")

        task_class = Task.registry[task_type]
        kwargs = data.get("kwargs", {})

        obj = task_class(
            title=kwargs.get("title", ""),
            description=kwargs.get("description", ""),
            status=kwargs.get("status", "pending")
        )

        for key, value in kwargs.items():
            if key not in ["title", "description", "status", "created"]:
                setattr(obj, key, value)

        if "created" in data:
            obj.created = datetime.strptime(data["created"], "%Y-%m-%d %H:%M:%S")
        return obj


class RegularTask(Task):
    def __init__(self, title, description="", status="pending", deadline=None):
        super().__init__(title, description, status)
        self.deadline = deadline

    def __str__(self):
        return f"[ ] {self.title} ({self.status}) - deadline: {self.deadline}"

    def to_dict(self):
        data = super().to_dict()
        data["kwargs"]["deadline"] = self.deadline
        return data


class PriorityTask(Task):
    PRIORITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    def __init__(self, title, description="", status="pending", priority="MEDIUM"):
        super().__init__(title, description, status)
        self.priority = priority.upper()

    def __str__(self):
        return f"[!] {self.title} ({self.status}) - priorytet: {self.priority}"

    def to_dict(self):
        return {**super().to_dict(), "priority": self.priority}


class RecurringTask(Task):
    def __init__(self, title, description="", status="pending", interval_days=7, start_date=None):
        super().__init__(title, description, status)
        self.interval_days = interval_days
        self.start_date = start_date or datetime.now().strftime("%Y-%m-%d")

    def __str__(self):
        next_date = (datetime.strptime(self.start_date, "%Y-%m-%d") +
                     timedelta(days=self.interval_days)).strftime("%Y-%m-%d")
        return f"[o] {self.title} ({self.status}) - co {self.interval_days} dni (nastepne: {next_date})"

    def to_dict(self):
        return {**super().to_dict(), "interval_days": self.interval_days, "start_date": self.start_date}


class Project:
    def __init__(self, name):
        self.name = name
        self.tasks = []
        self.current_date = datetime.now()

    def set_date(self, new_date):
        if isinstance(new_date, str):
            self.current_date = datetime.strptime(new_date, "%Y-%m-%d")
        else:
            self.current_date = new_date
        print(f"Data projektu ustawiona na: {self.current_date.strftime('%Y-%m-%d')}")

    def add_task(self, task):
        self.tasks.append(task)
        print(f"Dodano zadanie: {task.title}")

    def __iter__(self):
        return iter(self.tasks)

    def show_tasks(self):
        if not self.tasks:
            print("Brak zadan.")
            return
        print(f"\n===== Zadania w projekcie '{self.name}' =====")
        for t in self.tasks:
            print("-", t)

    def get_active_tasks(self):
        return [t for t in self.tasks if t.status != "done"]

    def get_overdue_tasks(self):
        overdue = []
        for t in self.tasks:
            if isinstance(t, RegularTask) and t.deadline and t.status != "done":
                deadline = datetime.strptime(t.deadline, "%Y-%m-%d")
                if deadline < self.current_date:
                    overdue.append(t)
        return overdue

    def mark_task_done(self, title):
        for t in self.tasks:
            if t.title == title:
                t.status = "done"
                print(f"Zadanie '{title}' oznaczono jako 'done'.")
                return
        print("Nie znaleziono zadania.")

    def mark_task_in_progress(self, title):
        for t in self.tasks:
            if t.title == title:
                t.status = "in progress"
                print(f"Zadanie '{title}' oznaczono jako 'in progress'.")
                return
        print("Nie znaleziono zadania.")

    def sort_tasks(self, criterion="created"):
        if criterion == "deadline":
            self.tasks.sort(key=lambda t: getattr(t, 'deadline', '9999-12-31'))
        elif criterion == "priority":
            self.tasks.sort(key=lambda t: -PriorityTask.PRIORITY_ORDER.get(getattr(t, 'priority', ''), 0))
        else:
            self.tasks.sort()
        print(f"Zadania posortowane wedlug: {criterion}")

    def to_json(self):
        data = {
            "name": self.name,
            "current_date": self.current_date.strftime("%Y-%m-%d %H:%M:%S"),
            "tasks": [t.to_dict() for t in self.tasks]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        project = cls(data.get("name", "Unnamed Project"))

        if "current_date" in data:
            project.current_date = datetime.strptime(data["current_date"], "%Y-%m-%d %H:%M:%S")

        for task_data in data.get("tasks", []):
            project.tasks.append(Task.from_dict(task_data))

        return project

    def save(self, filename="tasks.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "name": self.name,
                "current_date": self.current_date.strftime("%Y-%m-%d %H:%M:%S"),
                "tasks": [t.to_dict() for t in self.tasks]
            }, f, indent=2, ensure_ascii=False)
        print(f"Zapisano do {filename}")

    def load(self, filename="tasks.json"):
        try:
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
                self.name = data.get("name", self.name)
                if "current_date" in data:
                    self.current_date = datetime.strptime(data["current_date"], "%Y-%m-%d %H:%M:%S")
                self.tasks = [Task.from_dict(d) for d in data.get("tasks", [])]
            print(f"Wczytano z {filename}")
        except FileNotFoundError:
            print("Nie ma pliku.")


def main():
    project = Project("Moje zadania")

    while True:
        print("\n===== MENU =====")
        print("1. Dodaj RegularTask")
        print("2. Dodaj PriorityTask")
        print("3. Dodaj RecurringTask")
        print("4. Pokaż wszystkie zadania")
        print("5. Pokaż zadania aktywne")
        print("6. Pokaż zadania po terminie")
        print("7. Oznacz zadanie jako 'in progress'")
        print("8. Oznacz zadanie jako 'done'")
        print("9. Sortuj zadania")
        print("10. Ustaw datę projektu")
        print("11. Zapisz do pliku")
        print("12. Wczytaj z pliku")
        print("0. Zakończ")

        choice = input("Wybierz: ")

        if choice == "1":
            title = input("Tytuł: ")
            desc = input("Opis: ")
            deadline = input("Deadline (YYYY-MM-DD lub Enter): ") or (datetime.now() + timedelta(days=7)).strftime(
                "%Y-%m-%d")
            project.add_task(RegularTask(title, desc, deadline=deadline))

        elif choice == "2":
            title = input("Tytuł: ")
            desc = input("Opis: ")
            priority = input("Priorytet (LOW/MEDIUM/HIGH): ").upper() or "MEDIUM"
            project.add_task(PriorityTask(title, desc, priority=priority))

        elif choice == "3":
            title = input("Tytul: ")
            desc = input("Opis: ")
            interval = int(input("Co ile dni powtarzac: ") or 7)
            start = input("Data startu (YYYY-MM-DD lub Enter): ") or None
            project.add_task(RecurringTask(title, desc, interval_days=interval, start_date=start))

        elif choice == "4":
            project.show_tasks()

        elif choice == "5":
            print("\n===== Zadania aktywne =====")
            for t in project.get_active_tasks():
                print("-", t)

        elif choice == "6":
            print("\n===== Zadania po terminie =====")
            overdue = project.get_overdue_tasks()
            if not overdue:
                print("Brak zadan po terminie.")
            for t in overdue:
                print("-", t)

        elif choice == "7":
            title = input("Podaj tytu zadania: ")
            project.mark_task_in_progress(title)

        elif choice == "8":
            title = input("Podaj tytul zadania: ")
            project.mark_task_done(title)

        elif choice == "9":
            criterion = input("Sortuj wedlug (created/deadline/priority): ") or "created"
            project.sort_tasks(criterion)

        elif choice == "10":
            date_str = input("Nowa data (YYYY-MM-DD): ")
            try:
                project.set_date(date_str)
            except ValueError:
                print("Nieprawidlowy format")

        elif choice == "11":
            project.save()

        elif choice == "12":
            project.load()

        elif choice == "0":
            break

        else:
            print("Zostala wybrana zla opcja.")


if __name__ == "__main__":
    main()