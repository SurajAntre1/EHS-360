// $(function() {
//     'use strict'

//     var ticksStyle = {
//         fontColor: '#495057',
//         fontStyle: 'bold'
//     }

//     var mode = 'index'
//     var intersect = true

//     var $salesChart = $('#sales-chart')
//     var salesChart = new Chart($salesChart, {
//         type: 'bar',
//         data: {
//             labels: ['JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'],
//             datasets: [{
//                     backgroundColor: '#007bff',
//                     borderColor: '#007bff',
//                     data: [1000, 2000, 3000, 2500, 2700, 2500, 3000]
//                 },
//                 {
//                     backgroundColor: '#ced4da',
//                     borderColor: '#ced4da',
//                     data: [700, 1700, 2700, 2000, 1800, 1500, 2000]
//                 }
//             ]
//         },
//         options: {
//             maintainAspectRatio: false,
//             tooltips: {
//                 mode: mode,
//                 intersect: intersect
//             },
//             hover: {
//                 mode: mode,
//                 intersect: intersect
//             },
//             legend: {
//                 display: false
//             },
//             scales: {
//                 yAxes: [{
//                     // display: false,
//                     gridLines: {
//                         display: true,
//                         lineWidth: '4px',
//                         color: 'rgba(0, 0, 0, .2)',
//                         zeroLineColor: 'transparent'
//                     },
//                     ticks: $.extend({
//                         beginAtZero: true,

//                         // Include a dollar sign in the ticks
//                         callback: function(value, index, values) {
//                             if (value >= 1000) {
//                                 value /= 1000
//                                 value += 'k'
//                             }
//                             return '$' + value
//                         }
//                     }, ticksStyle)
//                 }],
//                 xAxes: [{
//                     display: true,
//                     gridLines: {
//                         display: false
//                     },
//                     ticks: ticksStyle
//                 }]
//             }
//         }
//     })

//     var $visitorsChart = $('#visitors-chart')
//     var visitorsChart = new Chart($visitorsChart, {
//         data: {
//             labels: ['18th', '20th', '22nd', '24th', '26th', '28th', '30th'],
//             datasets: [{
//                     type: 'line',
//                     data: [100, 120, 170, 167, 180, 177, 160],
//                     backgroundColor: 'transparent',
//                     borderColor: '#007bff',
//                     pointBorderColor: '#007bff',
//                     pointBackgroundColor: '#007bff',
//                     fill: false
//                         // pointHoverBackgroundColor: '#007bff',
//                         // pointHoverBorderColor    : '#007bff'
//                 },
//                 {
//                     type: 'line',
//                     data: [60, 80, 70, 67, 80, 77, 100],
//                     backgroundColor: 'tansparent',
//                     borderColor: '#ced4da',
//                     pointBorderColor: '#ced4da',
//                     pointBackgroundColor: '#ced4da',
//                     fill: false
//                         // pointHoverBackgroundColor: '#ced4da',
//                         // pointHoverBorderColor    : '#ced4da'
//                 }
//             ]
//         },
//         options: {
//             maintainAspectRatio: false,
//             tooltips: {
//                 mode: mode,
//                 intersect: intersect
//             },
//             hover: {
//                 mode: mode,
//                 intersect: intersect
//             },
//             legend: {
//                 display: false
//             },
//             scales: {
//                 yAxes: [{
//                     // display: false,
//                     gridLines: {
//                         display: true,
//                         lineWidth: '4px',
//                         color: 'rgba(0, 0, 0, .2)',
//                         zeroLineColor: 'transparent'
//                     },
//                     ticks: $.extend({
//                         beginAtZero: true,
//                         suggestedMax: 200
//                     }, ticksStyle)
//                 }],
//                 xAxes: [{
//                     display: true,
//                     gridLines: {
//                         display: false
//                     },
//                     ticks: ticksStyle
//                 }]
//             }
//         }
//     })
// })

// $(document).ready(function() {
//     showClicksGraph();
// });

// function showClicksGraph() {

//     var ticksStyle = {
//         fontColor: '#495057',
//         fontStyle: 'bold'
//     }

//     var base_url = $('#base_url').val();
//     var account_id = $('#account_id').val();
//     var labels = [];
//     var clicks = [];
//     var conversions = [];
//     var mode = 'index';
//     var intersect = true;
//     $.ajax({
//         type: "POST",
//         url: base_url + "user/ajax/get_click_chart_data",
//         datatype: "json",
//         data: { 'account_id': account_id },
//         async: false,
//         success: function(data) {
//             var clicks_data = $.parseJSON(data);
//             clicks = clicks_data.clicks;
//             labels = clicks_data.labels;
//             conversions = clicks_data.conversions;
//             max_clicks = Math.max.apply(Math, clicks);
//             max_conversions = Math.max.apply(Math, conversions);

//             var total_clicks = clicks.reduce(function(a, b) {
//                 return a + b;
//             }, 0);
//             var total_conversions = conversions.reduce(function(a, b) {
//                 return a + b;
//             }, 0);

//             $('.offer-alltime-clicks').text(total_clicks);
//             $('.offer-alltime-conversions').text(total_conversions);
//         },
//     });
//     var $clicksChart = $('#clicks-chart');
//     var clicksChart = new Chart($clicksChart, {
//         data: {
//             labels: labels,
//             datasets: [{
//                     type: 'line',
//                     data: clicks,
//                     backgroundColor: 'transparent',
//                     borderColor: '#007bff',
//                     pointBorderColor: '#007bff',
//                     pointBackgroundColor: '#007bff',
//                     fill: false
//                         // pointHoverBackgroundColor: '#007bff',
//                         // pointHoverBorderColor    : '#007bff'
//                 },
//                 {
//                     type: 'line',
//                     data: conversions,
//                     backgroundColor: 'tansparent',
//                     borderColor: '#ced4da',
//                     pointBorderColor: '#ced4da',
//                     pointBackgroundColor: '#ced4da',
//                     fill: false
//                         // pointHoverBackgroundColor: '#ced4da',
//                         // pointHoverBorderColor    : '#ced4da'
//                 }
//             ]
//         },
//         options: {
//             maintainAspectRatio: false,
//             tooltips: {
//                 mode: mode,
//                 intersect: intersect
//             },
//             hover: {
//                 mode: mode,
//                 intersect: intersect
//             },
//             legend: {
//                 display: false
//             },
//             scales: {
//                 yAxes: [{
//                     display: true,
//                     gridLines: {
//                         display: true,
//                         lineWidth: '4px',
//                         color: 'rgba(0, 0, 0, .2)',
//                         // zeroLineColor: 'transparent',
//                         zeroLineColor: 'rgba(0, 0, 0, .25)',
//                     },
//                     ticks: $.extend({
//                         beginAtZero: true,
//                         // max: Math.max(clicks),
//                         suggestedMax: max_clicks + 1,
//                         stepSize: 1,
//                     }, ticksStyle)
//                 }],
//                 xAxes: [{
//                     display: true,
//                     gridLines: {
//                         display: false,
//                     },
//                     ticks: ticksStyle
//                 }]
//             }
//         }
//     })
// }