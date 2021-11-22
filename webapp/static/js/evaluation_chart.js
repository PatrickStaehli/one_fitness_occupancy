Chart.defaults.color = "#ffffff";

function look_for_existing_center(center_name){
    dataset_index = -1
    for (i=0; i<(occupancy_scatterplot.data.datasets).length; i++){
        if (occupancy_scatterplot.data.datasets[i].label == center_name){
            dataset_index = i
        }
    }
    // If dataset not exists yet
    if(dataset_index == -1){
        create_new_dataset(center_name)
        dataset_index = (occupancy_scatterplot.data.datasets).length-1
    }
    return dataset_index
}

function create_new_dataset(center_name){
    const randomColor = Math.floor(Math.random()*16777215).toString(16);
    occupancy_scatterplot.data.datasets.push({ 
            data: [],
            label: center_name,
            borderColor: "#" + randomColor,
            pointBorderColor: "#" + randomColor,
            pointBackgroundColor:  "#" + randomColor,
            fill: false,
            showLine: false,
            pointRadius: 4
        })
}

function update_occupancy_plot(data){
        $.each(data, function(key, value) {
            dataset_index = look_for_existing_center(value.centre_name);
            occupancy_scatterplot.data.datasets[dataset_index].data.push(value.currentVisitors)

            // Timestamp to date
            var date = new Date(value.timestamp);
            var formatted_date = date.getDate() + '.' + date.getMonth()
            if(!occupancy_scatterplot.data.labels.includes(formatted_date)){
                occupancy_scatterplot.data.labels.push(formatted_date);
            }
            
    });
    occupancy_scatterplot.update();
}
$.getJSON("api/one_training/daily_occupancy", update_occupancy_plot);

var ctx = document.getElementById('line-chart').getContext('2d');
let ChartOptions = {
    plugins: {
        title: {
            display: true,
            text: 'Tägliche durchschnittliche Auslastung',
            font: {
                size: 30,
                fontColor: 'white'
            }
        },
        tooltip: {
            callbacks: {
                title: function(tooltipItem, data) {
                    return console.log(tooltipItem);
                },
                label: function(tooltipItem, data) {
                    return occupancy_scatterplot.data['labels'][tooltipItem['index']];
                }
            }
        }
    },
    scales: {
        x: {
            grid: {
                color: "#ffffff"
            },
            title:{
                display: true,
                text: 'Datum',
                font: {
                    size: 25
                }
            }
            
        },
        y: {
            grid: {
                color: "#ffffff"
            },
            title:{
                display: true,
                text: 'Durchschnitt der anwesenden Besucher',
                font: {
                    size: 20
                }
            }
        }
    }
};
occupancy_scatterplot = new Chart(ctx, {
    type: 'line',
    options: ChartOptions,
    data: {
        labels: [],
        datasets: []
    }
                
});