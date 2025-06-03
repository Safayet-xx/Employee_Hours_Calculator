from django.shortcuts import render
from django.http import HttpResponse
import pandas as pd
from datetime import datetime
import io

def calculate_minutes_worked(entries):
    if len(entries) == 3:
        t1 = datetime.strptime(entries[0], "%H:%M")
        t2 = datetime.strptime(entries[2], "%H:%M")
        total = (t2 - t1).total_seconds() / 60 - 30  # subtract 30 minutes break
        return int(max(total, 0))
    total_minutes = 0
    for i in range(0, len(entries) - 1, 2):
        t1 = datetime.strptime(entries[i], "%H:%M")
        t2 = datetime.strptime(entries[i + 1], "%H:%M")
        diff = (t2 - t1).total_seconds() / 60
        if diff > 0:
            total_minutes += diff
    return int(total_minutes)

def upload_file_view(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        df = pd.read_excel(file)

        names = []
        name_rows = []
        for i in range(0, len(df), 2):
            name = df.iloc[i, 0]
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
                name_rows.append(i)

        data = []
        max_day = max([int(col.split(' ')[-1]) for col in df.columns if col.startswith('Day ')], default=30)

        for i, name in zip(name_rows, names):
            for day in range(1, max_day + 1):
                col = f"Day {day}"
                if col in df.columns:
                    val = df.at[i, col]
                    if isinstance(val, str):
                        times = val.strip().split('\n')
                        minutes = calculate_minutes_worked(times)
                        data.append({"Employee": name, "Day": day, "Minutes Worked": minutes})

        df_minutes = pd.DataFrame(data)
        df_pivot = df_minutes.pivot(index="Day", columns="Employee", values="Minutes Worked").fillna(0).astype(int)
        df_pivot = df_pivot.reindex(range(1, max_day + 1), fill_value=0)

        # Totals
        total_minutes_series = df_pivot.sum()
        df_pivot.loc['Total (min)'] = total_minutes_series
        df_pivot.loc['Total (hr:min)'] = total_minutes_series.apply(lambda x: f"{int(x // 60)}h {int(x % 60)}m")

        # Grand total
        total_all_minutes = total_minutes_series.sum()
        total_all_hours = int(total_all_minutes // 60)
        total_all_remaining_minutes = int(total_all_minutes % 60)
        grand_total_str = f"{total_all_hours}h {total_all_remaining_minutes}m"
        df_pivot.loc['Grand Total (hr:min)'] = [grand_total_str] + [''] * (len(df_pivot.columns) - 1)

        if 'download' in request.POST:
            csv_stream = io.StringIO()
            df_pivot.to_csv(csv_stream)
            response = HttpResponse(csv_stream.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="minutes_summary.csv"'
            return response

        return render(request, 'tracker/results.html', {
            'table_html': df_pivot.to_html(classes="table", index=True),
            'download_available': True
        })

    return render(request, 'tracker/upload.html')
