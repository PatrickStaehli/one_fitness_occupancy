/*






*/



/*
Defines the settings of the line chart with a filled area around the curve (e.g. to plot the standard deviation)
*/
Chart.defaults.stripe = Chart.helpers.clone(Chart.defaults.line);
Chart.controllers.stripe = Chart.controllers.line.extend({
  draw: function(ease) {
	var result = Chart.controllers.line.prototype.draw.apply(this, arguments);

	// don't render the stripes till we've finished animating
	if (!this.rendered && ease !== 1)
	  return;
	this.rendered = true;


	var helpers = Chart.helpers;
	var meta = this.getMeta();
	var yScale = this.getScaleForId(meta.yAxisID);
	var yScaleZeroPixel = yScale.getPixelForValue(0);
	var widths = this.getDataset().width;
	var ctx = this.chart.chart.ctx;

	ctx.save();
	ctx.fillStyle = this.getDataset().backgroundColor;
	ctx.lineWidth = 0;
	ctx.beginPath();

	// initialize the data and bezier control points for the top of the stripe
	helpers.each(meta.data, function(point, index) {
	  point._view.y += (yScale.getPixelForValue(widths[index]) - yScaleZeroPixel);
	});
	Chart.controllers.line.prototype.updateBezierControlPoints.apply(this);

	// draw the top of the stripe
	helpers.each(meta.data, function(point, index) {
	  if (index === 0)
		ctx.moveTo(point._view.x, point._view.y);
	  else {
		var previous = helpers.previousItem(meta.data, index);
		var next = helpers.nextItem(meta.data, index);

		Chart.elements.Line.prototype.lineToNextPoint.apply({
		  _chart: {
			ctx: ctx
		  }
		}, [previous, point, next, null, null])
	  }
	});

	// revert the data for the top of the stripe
	// initialize the data and bezier control points for the bottom of the stripe
	helpers.each(meta.data, function(point, index) {
	  point._view.y -= 2 * (yScale.getPixelForValue(widths[index]) - yScaleZeroPixel);
	});
	// we are drawing the points in the reverse direction
	meta.data.reverse();
	Chart.controllers.line.prototype.updateBezierControlPoints.apply(this);

	// draw the bottom of the stripe
	helpers.each(meta.data, function(point, index) {
	  if (index === 0)
		ctx.lineTo(point._view.x, point._view.y);
	  else {
		var previous = helpers.previousItem(meta.data, index);
		var next = helpers.nextItem(meta.data, index);

		Chart.elements.Line.prototype.lineToNextPoint.apply({
		  _chart: {
			ctx: ctx
		  }
		}, [previous, point, next, null, null])
	  }

	});

	// revert the data for the bottom of the stripe
	meta.data.reverse();
	helpers.each(meta.data, function(point, index) {
	  point._view.y += (yScale.getPixelForValue(widths[index]) - yScaleZeroPixel);
	});
	Chart.controllers.line.prototype.updateBezierControlPoints.apply(this);

	ctx.stroke();
	ctx.closePath();
	ctx.fill();
	ctx.restore();

	return result;
  }
});


// Line Chart for prediction
var config = {
  type: 'stripe',
  data: {
	labels: [],
	datasets: [{
	  label: "Erwartete Auslasung",
	  fill: false,
	  data: [],
	  width: [],
	  borderColor: "rgba(75,192,192,1)",
	  backgroundColor: "rgba(75,192,192,0.4)",
	  pointRadius: 0
	},
	{
	  label: 'Maximale Auslastung',
	  xAxisID:'xAxis1',
	  borderColor:"rgba(0,0,0,0.8)",
	  backgroundColor : "rgba(0,0,0,0)",
	  pointRadius: 0,
	  data: [],
	  width: []
	}]
  },
  options:{
	responsive: true,
	maintainAspectRatio: false,
	scales:{
	  xAxes:[
		{
		  id:'xAxis1',
		  type:"category",
		  ticks:{
			callback:function(label){
			  var time = label.split(";")[0];
			  var day = label.split(";")[1];
			  return time;
			}
		  },
		  autoSkip: true
		},
		{
		  id:'xAxis2',
		  type:"category",
		  scaleFontSize: 100,
		  gridLines: {
			drawOnChartArea: false,
			display : false // only want the grid lines for one axis to show up
		  },
		  ticks:{
			fontSize: 20,
			autoSkip: false,
			maxRotation: 0,
			minRotation: 0,
			callback:function(label){
			  var time = label.split(";")[0];
			  var day = label.split(";")[1];
			  // To show the day lable only once a day, it is plotted only when the lable of xAxis1 is 13:15. 
			  // Since only every second label on x_axis is plotted, it can happen that 13:15 is empty. In this case, the day is plotted at 13:30
			  if(JSON.stringify(time) === JSON.stringify("13:15")){
				return day;
			  }else if(JSON.stringify(time) === JSON.stringify("13:30")){
				return day;
			  }else{
				return "";
			  }
			}
			
		  }
		}],
	  yAxes:[{
		ticks:{
		  beginAtZero:true
		}
	  }]
	}
  }
};

var ctx = document.getElementById("centre_prediction_occupancy_linechart").getContext("2d");
var prediction_occupancy_linechart = new Chart(ctx, config);

// request the data for a given centre via the API defined in main.py.
function update_occupancy_plot(data) {
	
	centre_prediction_occupancy_title.innerText = 'Erwartete Auslastung in ' + data.centre_properties.name;
	
	// Reset the dataset
	// Mean occupancy
	prediction_occupancy_linechart.data.datasets[0].data = [];
	prediction_occupancy_linechart.data.datasets[0].width = [];
	// Standard deviation
	prediction_occupancy_linechart.data.datasets[1].data = [];
	prediction_occupancy_linechart.data.datasets[1].width = [];
	// Labels
	prediction_occupancy_linechart.data.labels = [];
	
	var index = 0;
	
	// for each datapoint in the history, add it to the line plot. 
	$.each(data.occupancy_history, function(key, value) {
		
		// Push occupancy to chart if time is larger than 06:00
		if (key.split(':')[0]>=6 && key.split(':')[0]<22) {
			
			// Mean occupancy at time t
			prediction_occupancy_linechart.data.datasets[0].data.push(value.occupancy)
			prediction_occupancy_linechart.data.datasets[0].width.push(value.occupancy_std)
			
			// Standard deviation of the occupancy at time t
			prediction_occupancy_linechart.data.datasets[1].data.push(value.max_occupancy)
			prediction_occupancy_linechart.data.datasets[1].width.push(0)
			
			// Only every second label is plottet.
			if (index%2 ==0){
				prediction_occupancy_linechart.data.labels.push(key)
			}else{
				prediction_occupancy_linechart.data.labels.push('')
			}	
			index++;	
		}
	});
	
	// Update the chart	
	prediction_occupancy_linechart.update();
}


function update_history_chart(centre_id){
	$.getJSON("one_occupancy/api/one_training/occupancy?centre_id="+ centre_id, update_occupancy_plot);
}

// On page load, load first centre
$.getJSON("one_occupancy/api/one_training/occupancy?centre_id="+ 116, update_occupancy_plot);






