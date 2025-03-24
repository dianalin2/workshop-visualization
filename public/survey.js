const allResponsesDiv = document.getElementById('allResponses');

function createChart(surveys, id, title, chartType) {
    const canvas = document.getElementById(id);
    const ctx = canvas.getContext('2d');

    const data = {
        labels: Object.keys(surveys),
        datasets: [{
            label: 'Responses',
            data: Object.values(surveys),
        }],
    };

    console.log(data)

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: {
                display: true,
                text: `Survey Responses (by ${title})`,
                font: {
                    size: 20
                }
            },
            legend: {
                display: false,
                position: 'top',
                labels: {
                    font: {
                        size: 16
                    }
                }
            },
            labels: chartType === 'pie' ? {
                render: 'label'
            } : undefined
        }
    };

    const chart = new Chart(ctx, {
        type: chartType,
        data: data,
        options: options,
    });

    return chart;
}

async function refresh() {
    {
        const response = await fetch('/data/survey');
        const data = await response.json();

        const headers = {
            'Q1': 'Position',
            'Q2': 'Department',
            'Q3': 'Topics',
            'Q3A': 'Topics (Other)',
            'Q4': 'Specific Tools for Topics',
            'Q5': 'Meeting Format',
            'Q6': 'Time',
            'Q7': 'Length',
            'Q8': 'Additional Comments?'
        }

        const headerRow = document.createElement('tr');
        Object.keys(data[0]).forEach(header => {
            const th = document.createElement('th');
            th.innerText = header in headers ? headers[header] : header
            headerRow.appendChild(th);
        });

        allResponsesDiv.appendChild(headerRow);

        data.forEach(row => {
            const r = document.createElement('tr');
            const keys = Object.keys(row);
            r.ariaLabel = row['ResponseId'];

            keys.forEach(key => {
                const td = document.createElement('td');
                td.innerText = row[key];
                r.appendChild(td);
            });

            allResponsesDiv.appendChild(r);
        });
    }

    {
        const response = await fetch('/data/survey/topics');
        const data = await response.json();

        createChart(data, 'topics-chart', 'Topics', 'bar');
    }

    {
        const response = await fetch('/data/survey/positions');
        const data = await response.json();

        createChart(data, 'positions-chart', 'Positions', 'pie');
    }

    {
        const response = await fetch('/data/survey/departments');
        const data = await response.json();

        createChart(data, 'departments-chart', 'Departments', 'pie');
    }
}

refresh();

