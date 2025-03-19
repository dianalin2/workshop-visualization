const chartsDiv = document.getElementById('charts');
const ctxs = [];
const charts = {};
const filters = {};
const allWorkshopsDiv = document.getElementById('all-workshops');

let currentCtxId = 'chart';

let currentFilters = {
    name: '',
    time: '',
    type: 'count',
    categorize: false,
};

let workshopData = null;

document.getElementById('refresh').addEventListener('click', refresh);

Chart.Tooltip.positioners.bottom = function (elements, eventPosition) {
    const pos = Chart.Tooltip.positioners.average(elements);

    if (!pos)
        return false;

    return {
        x: pos.x,
        y: this.chart.chartArea.bottom - 10,
    }
}

async function refresh() {
    allWorkshopsDiv.innerHTML = '';

    const response = await fetch('/data');
    const data = await response.json();

    data.map(row => {
        console.log(row.seats_taken, row.attendance);
        row['start'] = new Date(row['start']);
        row['end'] = new Date(row['end']);
        return row;
    });

    const tableData = data.map(row => {
        row = {
            'ID': row['id'],
            'Title': row['title'],
            'Time': `${row['start'].toLocaleString()} - ${row['end'].toLocaleTimeString()}`,
            'Presenter': row['presenter'],
            'Description': row['description'],
            'Tags': row['tags'].join(', \n'),
            'Attendees (Registrations)': `${row['attendance']}/${row['seats']} (${row['seats_taken']} regs.)`
        };

        return row;
    });

    const headers = Object.keys(tableData[0]);
    const headerRow = document.createElement('tr');
    headers.forEach(header => {
        const th = document.createElement('th');
        th.innerText = header;
        headerRow.appendChild(th);
    });

    allWorkshopsDiv.appendChild(headerRow);

    tableData.forEach(row => {
        const r = document.createElement('tr');
        const keys = Object.keys(row);
        r.ariaLabel = row['ID'];

        keys.forEach(key => {
            const td = document.createElement('td');
            td.innerText = row[key];
            r.appendChild(td);
        });

        allWorkshopsDiv.appendChild(r);
    });

    createChart(data, currentCtxId);
    showStats(data);

    workshopData = data;
}

function showChart(ctxId) {
    ctxs.forEach(ctxId => {
        const ctx = document.getElementById(ctxId);
        ctx.style.display = 'none';
    });

    const ctx = document.getElementById(ctxId);
    ctx.style.display = 'block';

    document.querySelectorAll('#chart-select button').forEach(button => {
        button.classList.remove('active');
    });

    document.querySelector(`#chart-select button[aria-label="${ctxId}"]`).classList.add('active');

    currentCtxId = ctxId;
    currentFilters = filters[ctxId];
}

function setFilterInputs(filters) {
    document.getElementById('time').value = filters.time;
    document.getElementById('name').value = filters.name;
    document.getElementById('graph-type').value = filters.type;
    document.getElementById('categorize').checked = filters.categorize;
    document.getElementById('tags').value = filters.tags ?? '';
    document.getElementById('drop-0').checked = filters.drop;

    try {
        const [start, end] = filters.date.split('-');
        document.getElementById('start-date').value = new Date(parseInt(start)).toISOString().split('T')[0];
        document.getElementById('end-date').value = new Date(parseInt(end)).toISOString().split('T')[0];
    } catch (error) {
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        console.error(error);
    }
}


function buildChart(ctxId, filtersArray) {
    const ctx = document.createElement('canvas');
    ctx.classList.add('chart');
    ctx.id = ctxId;
    chartsDiv.appendChild(ctx);
    ctxs.push(ctxId);
    filters[ctxId] = filtersArray;

    const button = document.createElement('button');
    button.ariaLabel = ctxId;
    button.textContent = ctxs.length;
    button.onclick = () => {
        showChart(ctxId);
        console.log(currentFilters);

        setFilterInputs(currentFilters);
        filterTable(workshopData, currentFilters);
    };

    chartSelect.appendChild(button);

    return ctx;
}

function createChart(data, ctxId) {
    let ctx = document.getElementById(ctxId);

    if (!ctx) {
        ctx = buildChart(ctxId, { ...currentFilters });
        showChart(ctxId);
    } else if (charts[ctxId]) {
        charts[ctxId].destroy();
    }

    charts[ctxId] = new Chart(ctx, {
        id: ctxId,
        type: 'bar',
        data: {
            labels: data.map(row => row['title']),
            datasets: [{
                label: 'Attendees',
                data: data.map(row => row['processed_attendance'] ?? row['attendance']),
                backgroundColor: '#798db8',
                datalabels: {
                    labels: {
                        title: null
                    }
                },
            }, {
                label: 'Registrations',
                data: data.map(row => row['processed_seats_taken'] ?? row['seats_taken']),
                backgroundColor: '#ff9080',
                datalabels: {
                    labels: {
                        title: null
                    }
                },
            }, {
                label: 'Capacity',
                data: data.map(row => row['processed_seats'] ?? row['seats']),
                backgroundColor: '#ffdbdb'
            }]
        },
        plugins: [{
            id: 'CustomCanvasColor',
            beforeDraw: (chart) => {
                const {
                    ctx,
                    chartArea: { top, right, bottom, left, width, height },
                    scales: { x, y },
                } = chart;
                ctx.save();
                data.forEach((row, i) => {
                    if (!row.start)
                        return;

                    switch (row.start.getMonth()) {
                        case 0:
                        case 1:
                        case 2:
                        case 3:
                        case 4:
                            ctx.fillStyle = 'rgba(220, 255, 174, 0.75)';
                            break;
                        case 5:
                        case 6:
                        case 7:
                            ctx.fillStyle = 'rgba(255, 255, 127, 0.65)';
                            break;
                        case 8:
                        case 9:
                        case 10:
                        case 11:
                            ctx.fillStyle = 'rgba(255, 194, 128, 0.75)';
                    }
                    ctx.fillRect(
                        left + i * (width / data.length),
                        top,
                        width / data.length,
                        height
                    );

                    // add stripes for afternoon workshops
                    if (row.start && row.start.getHours() >= 12) {
                        ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
                        for (let j = 0; j < 10; j++) {
                            ctx.fillRect(
                                left + i * (width / data.length),
                                top + j * (height / 10),
                                width / data.length,
                                height / 20
                            );
                        }
                    }
                });
                ctx.restore();
            }
        }, ChartDataLabels],
        options: {
            interaction: {
                mode: 'index'
            },
            plugins: {
                datalabels: {
                    anchor: 'end',
                    rotation: -90,
                    align: 'start',
                    formatter: (value, context) => {
                        const row = data[context.dataIndex];
                        return `${parseInt(row['attendance'])} / ${parseInt(row['seats_taken'])} / ${row['seats']}`;
                    }
                },
                title: {
                    display: true,
                    text: 'RC Workshops Spring 2024–Spring 2025',
                    font: {
                        size: 20
                    }
                },
                tooltip: {
                    xAlign: 'center',
                    yAlign: 'center',
                    position: 'bottom',
                    callbacks: {
                        title: context => {
                            const row = data[context[0].dataIndex];
                            if (currentFilters.type === 'percentage') {
                                return `${row['title']} (${(100 * parseInt(row['attendance']) / parseInt(row['seats'])).toFixed(2)}%)`;
                            } else if (currentFilters.type === 'count') {
                                return `${row['title']} (${parseInt(row['attendance'])}/${parseInt(row['seats'])}) (${row['seats_taken']} Registrations)`;
                            }
                        },
                        label: context => {
                            return null;
                        },
                        footer: context => {
                            if (currentFilters.categorize) {
                                const row = data[context[0].dataIndex];
                                return `Total: ${parseInt(row['attendance'])}/${parseInt(row['seats'])}`;
                            } else {
                                const row = data[context[0].dataIndex];
                                return `Start: ${new Date(row['start']).toLocaleString()}\nEnd: ${new Date(row['end']).toLocaleString()}`;
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    ticks: {
                        autoSkip: false,
                        maxRotation: 90,
                        minRotation: 60,
                    }
                },
                y: {
                    beginAtZero: true
                }
            },
            layout: {
                padding: {
                    left: 40,
                    right: 40,
                    top: 10,
                    bottom: 10
                }
            },
            chartArea: {
                backgroundColor: 'rgba(255, 255, 255, 0.5)'
            }
        }
    });
}

function saveCharts() {
    const savedCharts = {};

    ctxs.forEach(ctxId => {
        savedCharts[ctxId] = {
            filters: filters[ctxId]
        };
    });


    localStorage.setItem('charts', JSON.stringify(savedCharts));

    console.log('Saved charts');
    console.log(savedCharts);
}

function loadCharts() {
    const savedCharts = JSON.parse(localStorage.getItem('charts'));

    if (!savedCharts)
        return;

    for (const ctxId in charts) {
        charts[ctxId].destroy();
    }

    for (const ctxId in savedCharts) {
        const chart = savedCharts[ctxId];
        let ctx = document.getElementById(ctxId);

        if (!ctx) {
            ctx = buildChart(ctxId, chart.filters);
        } else {
            filters[ctxId] = chart.filters;
        }

        createChart(filter(workshopData, chart.filters), ctxId);
        filterTable(workshopData, chart.filters);
    }

    showChart(ctxs[0]);
    filterTable(workshopData, currentFilters);
    setFilterInputs(currentFilters);
}

function filterOperators(data, attribute, lambda) {
    let filteredData = [];

    attribute.split(' OR ').forEach(attr => {
        console.log(data.filter(row => lambda(row, attr)));
        filteredData = filteredData.concat(data.filter(row => lambda(row, attr)));
    });

    if (!attribute.includes('AND'))
        return filteredData;

    if (!attribute.includes('OR'))
        filteredData = data;

    attribute.split(' AND ').forEach(attr => {
        filteredData = filteredData.filter(row => lambda(row, attr));
    });

    return filteredData;
}

function filter(data, filters) {
    let filteredData = data;

    if (filters.drop) {
        filteredData = filteredData.filter(row => row['attendance'] > 0);
    }

    if (filters.name) {
        filteredData = filterOperators(filteredData, filters.name, (row, name) => row['title'].toLowerCase().includes(name.toLowerCase()));
    }

    if (filters.time) {
        filteredData = filterOperators(filteredData, filters.time, (row, time) => {
            const [start, end] = time.split('-');
            const startTime = parseInt(start.split(':')[0]) + parseInt(start.split(':')[1]) / 60;
            const endTime = parseInt(end.split(':')[0]) + parseInt(end.split(':')[1]) / 60;
            return (row.start.getHours() + row.start.getMinutes() / 60) >= startTime && (row.end.getHours() + row.end.getMinutes() / 60) <= endTime;
        });
    }

    if (filters.tags) {
        filteredData = filterOperators(filteredData, filters.tags, (row, tags) => {
            return row['tags'].includes(tags);
        });
    }

    if (filters.date) {
        filteredData = filterOperators(filteredData, filters.date, (row, date) => {
            const [start, end] = date.split('-').map(date => parseInt(date));
            return row.start >= new Date(start) && row.end <= new Date(end);
        });
    }

    // group by tags, each data point can belong to multiple tags
    if (filters.categorize) {
        const dataByTag = {};

        filteredData.forEach(row => {
            const tags = row['tags'];
            tags.forEach(tag => {
                if (!dataByTag[tag]) {
                    dataByTag[tag] = [];
                }

                dataByTag[tag].push(row);
            });
        });

        const newData = [];

        const sortedTags = Object.keys(dataByTag).sort((a, b) => a > b ? 1 : -1);

        for (const tag of sortedTags) {
            newData.push({
                title: tag,
                attendance: dataByTag[tag].reduce((acc, row) => acc + row['attendance'], 0),
                seats_taken: dataByTag[tag].reduce((acc, row) => acc + row['seats_taken'], 0),
                seats: dataByTag[tag].reduce((acc, row) => acc + row['seats'], 0),
                start: null,
                end: null,
            });
        }

        filteredData = newData;
    }

    if (filters.type) {
        filteredData = filteredData.map(row => {
            row = { ...row };
            if (filters.type === 'percentage') {
                row['processed_attendance'] = (row['attendance'] / row['seats']) * 100;
                row['processed_seats_taken'] = (row['seats_taken'] / row['seats']) * 100
                row['processed_seats'] = 100;
            }

            return row;
        });
    }

    filteredData = filteredData.sort((a, b) => a['start'] > b['start'] ? 1 : -1);

    return filteredData;
}

function showStats(data) {
    const totalAttendees = data.reduce((acc, row) => acc + row['attendance'], 0);
    const totalRegistrations = data.reduce((acc, row) => acc + row['seats_taken'], 0);
    const totalCapacity = data.reduce((acc, row) => acc + row['seats'], 0);
    document.getElementById('total-workshops').textContent = data.length;
    document.getElementById('total-attendees').textContent = totalAttendees;
    document.getElementById('total-capacity').textContent = totalCapacity;
    document.getElementById('total-registrations').textContent = totalRegistrations;
    document.getElementById('total-attendees-percentage').textContent = `${(totalAttendees / totalRegistrations * 100).toFixed(2)}%`;
}

function filterTable(data, filters) {
    filters = { ...filters };
    filters.categorize = false;
    const filteredData = filter(data, filters);

    showStats(filteredData);

    const rowIds = new Set(filteredData.map(row => row['id']));

    const rows = allWorkshopsDiv.querySelectorAll('tr');
    rows.forEach(row => {
        if (rowIds.has(parseInt(row.ariaLabel))) {
            row.style.display = 'table-row';
        } else {
            row.style.display = 'none';
        }
    });
}

function filterTime(data, start, end) {
    const filteredData = data.filter(row => row.start.getHours() >= start && row.end.getHours() <= end);
    return filteredData;
}

document.getElementById('time').addEventListener('change', (event) => {
    event.preventDefault();
    const value = event.target.value;

    currentFilters.time = value;

    createChart(filter(workshopData, currentFilters), currentCtxId);
    filterTable(workshopData, currentFilters);
});

document.getElementById('name').addEventListener('change', (event) => {
    event.preventDefault();
    const value = event.target.value;

    currentFilters.name = value;

    createChart(filter(workshopData, currentFilters), currentCtxId);
    filterTable(workshopData, currentFilters);
});

const chartSelect = document.getElementById('chart-select');

document.getElementById('make-new-chart').addEventListener('click', () => {
    const newCtxId = `chart-${ctxs.length}`;
    createChart(filter(workshopData, currentFilters), newCtxId);
    ctxId = newCtxId;
});

document.getElementById('graph-type').addEventListener('change', (event) => {
    const type = event.target.value;
    currentFilters.type = type;
    createChart(filter(workshopData, currentFilters), currentCtxId);
    filterTable(workshopData, currentFilters);
});

document.getElementById('categorize').addEventListener('change', (event) => {
    const categorize = event.target.checked;
    currentFilters.categorize = categorize;
    createChart(filter(workshopData, currentFilters), currentCtxId);
    filterTable(workshopData, currentFilters);
});

document.getElementById('tags').addEventListener('change', (event) => {
    const tags = event.target.value;
    currentFilters.tags = tags;
    createChart(filter(workshopData, currentFilters), currentCtxId);
    filterTable(workshopData, currentFilters);
});

document.getElementById('drop-0').addEventListener('change', (event) => {
    const drop = event.target.checked;
    currentFilters.drop = drop;
    createChart(filter(workshopData, currentFilters), currentCtxId);
    filterTable(workshopData, currentFilters);
});

function filterDateInput(event) {
    event.preventDefault();
    try {
        const start = new Date(document.getElementById('start-date').value).getTime() || '';
        const end = new Date(document.getElementById('end-date').value).getTime() || '';

        currentFilters.date = `${start}-${end}`;

        createChart(filter(workshopData, currentFilters), currentCtxId);
        filterTable(workshopData, currentFilters);
    } catch (error) {
        console.error(error);
    }
}

document.getElementById('start-date').addEventListener('change', filterDateInput);
document.getElementById('end-date').addEventListener('change', filterDateInput);

document.getElementById('save').addEventListener('click', saveCharts);
document.getElementById('load').addEventListener('click', loadCharts);

refresh();
