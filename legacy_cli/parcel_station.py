"""
Campus Parcel Station
Author: Jiantao Zhuo (SID: 550132220)

Run the interactive program:
    python3 parcel_station.py

Run an automatic demonstration:
    python3 parcel_station.py --demo

Run the built-in tests:
    python3 parcel_station.py --selftest

The program uses only the Python Standard Library.
"""

import random
import sys


ROWS = "ABCD"
COLUMNS = 5
FREE_STORAGE_DAYS = 3
FEE_PER_EXTRA_DAY = 1.0
DATA_FILE = "parcel_station_data.tsv"

COURIERS = [
    "Australia Post",
    "DHL",
    "FedEx",
    "SF Express",
    "Toll",
]

RECIPIENT_NAMES = [
    "Alice",
    "Chen",
    "Jordan",
    "Mia",
    "Noah",
    "Priya",
    "Sam",
]

RANDOM_EVENTS = [
    (
        "A quiet day. No special event.",
        "normal",
    ),
    (
        "Online shopping surge: two extra parcels arrived.",
        "surge",
    ),
    (
        "Network outage: pick-up is unavailable today.",
        "outage",
    ),
    (
        "Customer appreciation day: storage fees are waived today.",
        "free",
    ),
]


def clean_text(value, field_name, maximum_length):
    """Validate and normalise a text value entered by the user."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")

    cleaned = " ".join(value.split())
    if cleaned == "":
        raise ValueError(f"{field_name} cannot be empty.")
    if len(cleaned) > maximum_length:
        raise ValueError(
            f"{field_name} must be {maximum_length} characters or fewer."
        )
    return cleaned


class Package:
    """Represent one parcel stored in the station."""

    def __init__(
        self,
        courier,
        recipient,
        pickup_code,
        shelf_slot,
        day_stored,
    ):
        """Create a Package with all of its required information."""
        self.courier = clean_text(courier, "Courier", 30)
        self.recipient = clean_text(recipient, "Recipient", 30)
        self.pickup_code = clean_text(pickup_code, "Pickup code", 4)
        self.shelf_slot = clean_text(shelf_slot, "Shelf slot", 2)
        self.day_stored = int(day_stored)

        if self.day_stored < 1:
            raise ValueError("The stored day must be at least 1.")
        if not self.pickup_code.isdigit() or len(self.pickup_code) != 4:
            raise ValueError("The pickup code must contain four digits.")
        if (
            len(self.shelf_slot) != 2
            or self.shelf_slot[0] not in ROWS
            or not self.shelf_slot[1].isdigit()
        ):
            raise ValueError(f"Invalid shelf slot: {self.shelf_slot}")

    def days_waiting(self, current_day):
        """Return how many complete days this parcel has waited."""
        return current_day - self.day_stored

    def is_overdue(self, current_day):
        """Return True when the free storage period has ended."""
        return self.days_waiting(current_day) > FREE_STORAGE_DAYS

    def storage_fee(self, current_day):
        """Calculate the fee for every day after the free period."""
        extra_days = self.days_waiting(current_day) - FREE_STORAGE_DAYS
        if extra_days > 0:
            return extra_days * FEE_PER_EXTRA_DAY
        return 0.0

    def __str__(self):
        """Return a readable description used by print()."""
        return (
            f"[{self.pickup_code}] {self.courier} -> {self.recipient} "
            f"@ {self.shelf_slot} (stored on day {self.day_stored})"
        )


class Station:
    """Manage parcels, shelves, fees, reports, and saved data."""

    def __init__(self, data_file=DATA_FILE, auto_load=True):
        """Create a station and optionally load an existing data file."""
        self.data_file = data_file
        self.parcels = {}
        self.shelf = []
        for row in range(len(ROWS)):
            self.shelf.append([False] * COLUMNS)

        self.current_day = 1
        self.revenue = 0.0
        self.total_checkins = 0
        self.total_checkouts = 0
        self.checkins_today = 0
        self.checkouts_today = 0
        self.pickup_allowed = True
        self.free_storage_today = False
        self.last_event = "The station is ready for a new day."
        self.notice = ""

        if auto_load:
            self.load_data()

    def slot_to_index(self, slot):
        """Convert a slot name such as 'B3' into a row and column index."""
        if not isinstance(slot, str) or len(slot) != 2:
            raise ValueError(f"Invalid shelf slot: {slot}")

        row_letter = slot[0]
        column_text = slot[1]
        if row_letter not in ROWS or not column_text.isdigit():
            raise ValueError(f"Invalid shelf slot: {slot}")

        row_index = ROWS.index(row_letter)
        column_index = int(column_text) - 1
        if column_index < 0 or column_index >= COLUMNS:
            raise ValueError(f"Invalid shelf slot: {slot}")
        return row_index, column_index

    def find_free_slot(self):
        """
        Reserve and return the first free shelf slot.

        The reserved cell becomes True so the next search cannot use it.
        """
        for row in range(len(ROWS)):
            for column in range(COLUMNS):
                if not self.shelf[row][column]:
                    self.shelf[row][column] = True
                    return ROWS[row] + str(column + 1)
        return "FULL"

    def release_slot(self, slot):
        """Mark a parcel's old shelf position as free."""
        row_index, column_index = self.slot_to_index(slot)
        self.shelf[row_index][column_index] = False

    def generate_pickup_code(self):
        """Generate an unused four-digit pickup code."""
        code = str(random.randint(1000, 9999))
        while code in self.parcels:
            code = str(random.randint(1000, 9999))
        return code

    def check_in(self, courier, recipient, current_day=None):
        """Validate a parcel, assign a slot and code, and store it."""
        if current_day is None:
            current_day = self.current_day

        courier = clean_text(courier, "Courier", 30)
        recipient = clean_text(recipient, "Recipient", 30)
        slot = self.find_free_slot()
        if slot == "FULL":
            raise ValueError(
                "Shelf is full. Pick up a parcel before checking in another."
            )

        try:
            code = self.generate_pickup_code()
            parcel = Package(
                courier,
                recipient,
                code,
                slot,
                current_day,
            )
        except (TypeError, ValueError):
            # Do not keep a shelf cell reserved when creation fails.
            self.release_slot(slot)
            raise

        self.parcels[code] = parcel
        self.total_checkins += 1
        self.checkins_today += 1
        self.save_data()
        return parcel

    def pick_up(self, code, current_day=None):
        """
        Remove a parcel and return:
        (parcel, charged_fee, fee_before_discount).
        """
        if current_day is None:
            current_day = self.current_day
        if not self.pickup_allowed:
            raise ValueError(
                "Pick-up service is unavailable today because of an outage."
            )

        code = str(code).strip()
        if code not in self.parcels:
            raise ValueError("Invalid pickup code. Please check it and try again.")

        parcel = self.parcels[code]
        normal_fee = parcel.storage_fee(current_day)
        charged_fee = 0.0 if self.free_storage_today else normal_fee

        self.release_slot(parcel.shelf_slot)
        del self.parcels[code]
        self.revenue += charged_fee
        self.total_checkouts += 1
        self.checkouts_today += 1
        self.save_data()
        return parcel, charged_fee, normal_fee

    def search_by_recipient(self, query):
        """Return every parcel whose recipient contains the search text."""
        query = clean_text(query, "Search text", 30).lower()
        matches = []
        for parcel in self.parcels.values():
            if query in parcel.recipient.lower():
                matches.append(parcel)

        matches.sort(key=lambda parcel: parcel.shelf_slot)
        return matches

    def overdue_parcels(self):
        """Return all parcels that have exceeded the free period."""
        overdue = []
        for parcel in self.parcels.values():
            if parcel.is_overdue(self.current_day):
                overdue.append(parcel)
        overdue.sort(key=lambda parcel: parcel.day_stored)
        return overdue

    def daily_report(self):
        """Print an end-of-day summary with aligned text."""
        overdue_count = len(self.overdue_parcels())
        print("\n" + "=" * 48)
        print(f"DAILY REPORT - DAY {self.current_day}")
        print("=" * 48)
        print(f"{'Checked in today:':<28}{self.checkins_today:>6}")
        print(f"{'Checked out today:':<28}{self.checkouts_today:>6}")
        print(f"{'Parcels still in station:':<28}{len(self.parcels):>6}")
        print(f"{'Overdue parcels:':<28}{overdue_count:>6}")
        print(f"{'Storage fees collected:':<28}${self.revenue:>5.2f}")
        print("=" * 48)

    def print_shelf(self):
        """Print the two-dimensional shelf as a visual occupancy map."""
        occupied = len(self.parcels)
        total = len(ROWS) * COLUMNS
        print("\nSHELF MAP   [X] occupied   [.] empty")
        print("    " + " ".join(str(number) for number in range(1, COLUMNS + 1)))
        for row in range(len(ROWS)):
            line = ROWS[row] + "  "
            for column in range(COLUMNS):
                if self.shelf[row][column]:
                    line += "[X] "
                else:
                    line += "[.] "
            print(line)
        print(f"Occupancy: {occupied}/{total}")

    def stats_dashboard(self):
        """Print creative analytics about courier and overdue activity."""
        print("\n" + "-" * 48)
        print("STATION ANALYTICS DASHBOARD")
        print("-" * 48)

        if len(self.parcels) == 0:
            print("No parcels are currently stored.")
            print("The dashboard has no courier data to analyse.")
            print("-" * 48)
            return

        courier_counts = {}
        overdue_counts = {}
        for parcel in self.parcels.values():
            if parcel.courier in courier_counts:
                courier_counts[parcel.courier] += 1
            else:
                courier_counts[parcel.courier] = 1

            if parcel.is_overdue(self.current_day):
                if parcel.courier in overdue_counts:
                    overdue_counts[parcel.courier] += 1
                else:
                    overdue_counts[parcel.courier] = 1

        most_active_company = ""
        highest_count = 0
        for company in courier_counts:
            count = courier_counts[company]
            if count > highest_count:
                highest_count = count
                most_active_company = company

        overdue_count = len(self.overdue_parcels())
        overdue_rate = overdue_count / len(self.parcels) * 100
        occupancy_rate = (
            len(self.parcels) / (len(ROWS) * COLUMNS) * 100
        )

        print(f"Active couriers: {len(courier_counts)}")
        print(f"Most active courier: {most_active_company} ({highest_count})")
        print(f"Overdue rate: {overdue_rate:.1f}%")
        print(f"Shelf occupancy rate: {occupancy_rate:.1f}%")
        print(f"Lifetime check-ins: {self.total_checkins}")
        print(f"Lifetime check-outs: {self.total_checkouts}")

        print("\nParcels by courier:")
        for company in courier_counts:
            print(f"  {company:<20}{courier_counts[company]:>3}")

        print("\nOverdue parcels by courier:")
        if len(overdue_counts) == 0:
            print("  None")
        else:
            for company in overdue_counts:
                print(f"  {company:<20}{overdue_counts[company]:>3}")
        print("-" * 48)

    def advance_day(self):
        """Move to the next day and apply one random creative event."""
        self.current_day += 1
        self.checkins_today = 0
        self.checkouts_today = 0
        self.pickup_allowed = True
        self.free_storage_today = False

        event_text, event_type = random.choice(RANDOM_EVENTS)
        self.last_event = event_text

        if event_type == "surge":
            for number in range(2):
                courier = random.choice(COURIERS)
                recipient = random.choice(RECIPIENT_NAMES)
                try:
                    self.check_in(courier, recipient, self.current_day)
                except ValueError:
                    self.last_event += " The shelf became full."
                    break
        elif event_type == "outage":
            self.pickup_allowed = False
        elif event_type == "free":
            self.free_storage_today = True

        self.save_data()
        return self.last_event

    def save_data(self):
        """Write station data to a tab-separated text file."""
        if self.data_file is None:
            return True

        lines = []
        meta_fields = [
            "META",
            str(self.current_day),
            f"{self.revenue:.2f}",
            str(self.total_checkins),
            str(self.total_checkouts),
            str(self.checkins_today),
            str(self.checkouts_today),
            "1" if self.pickup_allowed else "0",
            "1" if self.free_storage_today else "0",
            self.last_event.replace("\t", " "),
        ]
        lines.append("\t".join(meta_fields))

        for parcel in self.parcels.values():
            fields = [
                "PACKAGE",
                parcel.pickup_code,
                parcel.courier,
                parcel.recipient,
                parcel.shelf_slot,
                str(parcel.day_stored),
            ]
            lines.append("\t".join(fields))

        try:
            with open(self.data_file, "w", encoding="utf-8") as file:
                for line in lines:
                    file.write(line + "\n")
        except OSError as error:
            self.notice = (
                f"Warning: data could not be saved ({error}). "
                "The current session can continue."
            )
            return False
        return True

    def load_data(self):
        """Load saved data safely without overwriting data after a bad file."""
        if self.data_file is None:
            return False

        try:
            with open(self.data_file, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except FileNotFoundError:
            return False
        except OSError as error:
            self.notice = f"Warning: saved data could not be read ({error})."
            return False

        try:
            if len(lines) == 0:
                raise ValueError("The saved file is empty.")

            meta_parts = lines[0].rstrip("\n").split("\t")
            if len(meta_parts) != 10 or meta_parts[0] != "META":
                raise ValueError("The saved file has invalid metadata.")

            current_day = int(meta_parts[1])
            revenue = float(meta_parts[2])
            total_checkins = int(meta_parts[3])
            total_checkouts = int(meta_parts[4])
            checkins_today = int(meta_parts[5])
            checkouts_today = int(meta_parts[6])
            pickup_allowed = meta_parts[7] == "1"
            free_storage_today = meta_parts[8] == "1"
            last_event = meta_parts[9]

            if current_day < 1 or revenue < 0:
                raise ValueError("The saved metadata is outside valid limits.")

            loaded_parcels = {}
            loaded_shelf = []
            for row in range(len(ROWS)):
                loaded_shelf.append([False] * COLUMNS)

            for line_number in range(1, len(lines)):
                line = lines[line_number].rstrip("\n")
                if line == "":
                    continue
                parts = line.split("\t")
                if len(parts) != 6 or parts[0] != "PACKAGE":
                    raise ValueError(
                        f"Invalid package record on line {line_number + 1}."
                    )

                code, courier, recipient, slot, stored_day = parts[1:]
                if code in loaded_parcels:
                    raise ValueError(f"Duplicate pickup code: {code}")

                parcel = Package(
                    courier,
                    recipient,
                    code,
                    slot,
                    int(stored_day),
                )
                row_index, column_index = self.slot_to_index(slot)
                if loaded_shelf[row_index][column_index]:
                    raise ValueError(f"Duplicate shelf slot: {slot}")
                loaded_shelf[row_index][column_index] = True
                loaded_parcels[code] = parcel

        except (IndexError, ValueError) as error:
            self.notice = (
                f"Warning: saved data was ignored because it was invalid "
                f"({error}). A new empty station was opened."
            )
            return False

        self.current_day = current_day
        self.revenue = revenue
        self.total_checkins = total_checkins
        self.total_checkouts = total_checkouts
        self.checkins_today = checkins_today
        self.checkouts_today = checkouts_today
        self.pickup_allowed = pickup_allowed
        self.free_storage_today = free_storage_today
        self.last_event = last_event
        self.parcels = loaded_parcels
        self.shelf = loaded_shelf
        return True


def show_welcome():
    """Print the title screen and a short feature summary."""
    print("=" * 54)
    print("              CAMPUS PARCEL STATION")
    print("                 校园快递驿站")
    print("=" * 54)
    print("Check in parcels, collect them by code, manage shelves,")
    print("track storage fees, and watch daily random events.")
    print("入库、取件、管理货架、统计滞留费，并体验每日随机事件。")
    print("=" * 54)


def show_menu(station):
    """Print the main menu and current day."""
    print(f"\n===== DAY {station.current_day} / 第 {station.current_day} 天 =====")
    print(f"Today's event / 今日事件: {station.last_event}")
    if not station.pickup_allowed:
        print("Pick-up is unavailable today. / 今天暂停取件。")
    if station.free_storage_today:
        print("Storage fees are waived today. / 今天免滞留费。")
    if station.notice != "":
        print(station.notice)
        station.notice = ""

    print("1. Check in a parcel       入库")
    print("2. Pick up a parcel        取件")
    print("3. Search by recipient     按收件人查询")
    print("4. Show shelf map          查看货架")
    print("5. Daily report            每日报表")
    print("6. Analytics dashboard     数据面板")
    print("7. Move to the next day    进入下一天")
    print("8. Exit                    退出")


def run_interactive():
    """Run the menu until the user chooses to exit."""
    station = Station()
    show_welcome()

    try:
        while True:
            show_menu(station)
            choice = input("Choose 1-8 / 请选择: ").strip()

            if choice == "1":
                try:
                    courier = input("Courier company / 快递公司: ")
                    recipient = input("Recipient name / 收件人: ")
                    parcel = station.check_in(courier, recipient)
                    print("\nParcel checked in successfully! / 包裹入库成功！")
                    print(f"Pickup code / 取件码: {parcel.pickup_code}")
                    print(f"Shelf slot / 货位: {parcel.shelf_slot}")
                except ValueError as error:
                    print(f"Error / 错误: {error}")

            elif choice == "2":
                try:
                    code = input("Enter the pickup code / 输入取件码: ")
                    parcel, fee, normal_fee = station.pick_up(code)
                    print(
                        f"\nCollected for {parcel.recipient}. "
                        f"Goodbye, parcel {parcel.pickup_code}!"
                    )
                    print(
                        f"已为 {parcel.recipient} 完成取件，"
                        f"包裹 {parcel.pickup_code} 已出库。"
                    )
                    if fee > 0:
                        print(f"Storage fee charged / 收取滞留费: ${fee:.2f}")
                    elif normal_fee > 0:
                        print(
                            "Today's event waived a fee of "
                            f"${normal_fee:.2f}. / 今日活动已免除滞留费。"
                        )
                    else:
                        print("No storage fee. / 无需支付滞留费。")
                except ValueError as error:
                    print(f"Error / 错误: {error}")

            elif choice == "3":
                try:
                    query = input(
                        "Recipient name or part of the name / 收件人姓名: "
                    )
                    matches = station.search_by_recipient(query)
                    if len(matches) == 0:
                        print("No matching parcels. / 没有找到匹配的包裹。")
                    else:
                        print(f"\nFound {len(matches)} parcel(s):")
                        for parcel in matches:
                            print("  " + str(parcel))
                except ValueError as error:
                    print(f"Error / 错误: {error}")

            elif choice == "4":
                station.print_shelf()

            elif choice == "5":
                station.daily_report()
                overdue = station.overdue_parcels()
                if len(overdue) > 0:
                    print("Overdue parcels:")
                    for parcel in overdue:
                        fee = parcel.storage_fee(station.current_day)
                        print(f"  {parcel} | fee now: ${fee:.2f}")

            elif choice == "6":
                station.stats_dashboard()

            elif choice == "7":
                event = station.advance_day()
                print(
                    f"\nWelcome to day {station.current_day}! "
                    f"/ 欢迎来到第 {station.current_day} 天！"
                )
                print(f"Morning news / 今日事件: {event}")
                station.daily_report()

            elif choice == "8":
                station.save_data()
                print("Thank you for using Campus Parcel Station. Goodbye!")
                print("感谢使用校园快递驿站，再见！")
                break

            else:
                print("Invalid choice. Please enter 1-8.")
                print("选择无效，请输入 1-8。")

    except (EOFError, KeyboardInterrupt):
        station.save_data()
        print("\nInput ended. Your data has been saved.")
        print("输入已结束，数据已保存。")

    return 0


def run_self_tests():
    """Run positive, negative, and edge-case checks."""
    print("Running Campus Parcel Station tests...")
    results = []

    def check(description, condition):
        """Print and record one test result."""
        if condition:
            print(f"[PASS] {description}")
            results.append(True)
        else:
            print(f"[FAIL] {description}")
            results.append(False)

    station = Station(data_file=None, auto_load=False)
    first = station.check_in("Australia Post", "Alice", 1)
    second = station.check_in("DHL", "Bob", 1)
    third = station.check_in("DHL", "Alice Chen", 1)

    check(
        "Positive: first parcel receives slot A1",
        first.shelf_slot == "A1",
    )
    check(
        "Positive: next parcel receives slot A2",
        second.shelf_slot == "A2",
    )
    check(
        "Edge: pickup codes are four digits",
        len(first.pickup_code) == 4 and first.pickup_code.isdigit(),
    )
    check(
        "Positive: friendlier recipient search is case-insensitive",
        len(station.search_by_recipient("alice")) == 2,
    )
    check(
        "Edge: exactly three days is still free",
        first.storage_fee(4) == 0.0,
    )
    check(
        "Positive: the fourth waiting day costs one dollar",
        first.storage_fee(5) == 1.0,
    )

    _, charged, _ = station.pick_up(first.pickup_code, 5)
    check("Positive: overdue fee is charged", charged == 1.0)

    fourth = station.check_in("FedEx", "Dana", 5)
    check(
        "Positive: a collected shelf spot is reused",
        fourth.shelf_slot == "A1",
    )

    try:
        station.pick_up("0000", 5)
        invalid_code_raised = False
    except ValueError:
        invalid_code_raised = True
    check("Negative: an invalid code raises ValueError", invalid_code_raised)

    try:
        station.check_in("", "Nobody", 5)
        empty_name_raised = False
    except ValueError:
        empty_name_raised = True
    check("Negative: an empty courier raises ValueError", empty_name_raised)

    full_station = Station(data_file=None, auto_load=False)
    for number in range(len(ROWS) * COLUMNS):
        full_station.check_in("DHL", f"Person {number}", 1)

    try:
        full_station.check_in("DHL", "Extra", 1)
        full_shelf_raised = False
    except ValueError:
        full_shelf_raised = True
    check("Edge: the twenty-first parcel is rejected", full_shelf_raised)

    passed = results.count(True)
    total = len(results)
    print(f"\nResult: {passed}/{total} tests passed.")
    return passed == total


def run_demo():
    """Run a deterministic tour that is useful for a presentation."""
    station = Station(data_file=None, auto_load=False)
    show_welcome()
    print("\nDEMONSTRATION MODE / 演示模式")

    alice_parcel = station.check_in("Australia Post", "Alice", 1)
    station.check_in("DHL", "Chen", 1)
    station.check_in("SF Express", "Mia", 1)

    print(f"\n1) Alice's parcel was stored at {alice_parcel.shelf_slot}.")
    print(f"   Pickup code: {alice_parcel.pickup_code}")
    station.print_shelf()
    station.daily_report()

    station.current_day = 7
    parcel, fee, _ = station.pick_up(alice_parcel.pickup_code)
    print("\n2) Alice collected her parcel on day 7.")
    print(f"   It waited {parcel.days_waiting(7)} days.")
    print(f"   Storage fee charged: ${fee:.2f}")

    station.print_shelf()
    station.stats_dashboard()
    station.daily_report()
    print("\nDemo complete. Run without --demo for the interactive menu.")
    return 0


def main(arguments):
    """Choose interactive, demonstration, or test mode."""
    if "--selftest" in arguments:
        return 0 if run_self_tests() else 1
    if "--demo" in arguments:
        return run_demo()
    return run_interactive()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
