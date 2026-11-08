Campus Parcel Station
Author: Jiantao Zhuo
SID: 550132220

================================================================
1. How to run / 如何运行
================================================================

Main interactive program:
    python3 parcel_station.py

Automatic presentation demo:
    python3 parcel_station.py --demo

Built-in tests:
    python3 parcel_station.py --selftest

No external libraries are required.
The program uses only Python's standard library.

Keep parcel_station.py and README.txt together in the Ed workspace.
The program creates parcel_station_data.tsv after the first operation.
That file stores the station data so the next run can continue.

================================================================
2. Controls / 操作
================================================================

1  Check in a parcel / 包裹入库
2  Pick up a parcel / 凭取件码取件
3  Search for a recipient / 按收件人查询
4  Show the shelf map / 显示货架占用图
5  Show the daily report / 显示每日报表
6  Show analytics / 显示数据面板
7  Move to the next day / 进入下一天
8  Exit and save / 退出并保存

Rules:
- The shelf contains 4 rows and 5 columns.
- Each new parcel receives the first free slot.
- Each parcel receives a unique four-digit pickup code.
- The first three waiting days are free.
- After that, the storage fee is $1 per extra day.
- A collected parcel frees its shelf slot immediately.
- Random morning events can create a parcel surge, stop pick-up,
  or waive storage fees for a day.

================================================================
3. Quick test / 快速测试
================================================================

Start the program and choose:
1 -> Australia Post -> Alice

Write down the printed pickup code and shelf slot.
Choose 5 to check that the parcel appears in the report.
Choose 7 four times to advance to day 5.
Choose 2 and enter the saved pickup code.
The parcel waited four days, so the fee is $1.

Then test an invalid code. The program prints an error but does not crash.

================================================================
4. Advanced concepts used / 使用的高级主题
================================================================

- Classes and Objects: Package and Station classes
- Exception handling: raise and try/except for invalid input and rules
- File Input/Output: save and load using open() and with
- Multi-dimensional lists: the 4 by 5 shelf
- Modular functions, type validation, __str__, and documentation

================================================================
5. Submission reminder / 提交提醒
================================================================

Submit the Python code files in the Ed Code Submission slide.
The Padlet post also needs:
- Project title
- A representative screenshot
- A short description including the target audience

Before submitting, run:
    python3 parcel_station.py --selftest
