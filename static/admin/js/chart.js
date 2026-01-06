var ctx = document.getElementById('myChart').getContext('2d');
var myChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['Red', 'Blue', 'Yellow', 'Green', 'Purple', 'Orange'],
        datasets: [
        {
            label: '# VIews',
            data: [12, 19, 3, 5, 2, 3],
            backgroundColor: [
                'transperent'
            ],
            borderColor: [
                'red'
            ],
            borderWidth: 1
        },
        {
            label: '# of Votes',
            data: [12, 9, 13, 5, 2, 31],
            backgroundColor: [
                'transperent'
            ],
            borderColor: [
                'blue'
            ],
            borderWidth: 1
            
        },
    ],
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});