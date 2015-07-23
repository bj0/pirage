/*** @jsx React.DOM */

var postUrl = "/click";
var listenUrl = "/stream";
var lockUrl = "/set_lock";
var pirUrl = "/set_pir";
var dweetUrl = "/set_dweet"

jQuery["postJSON"] = function( url, data, callback ) {
    // shift arguments if data argument was omitted
    if ( jQuery.isFunction( data ) ) {
        callback = data;
        data = undefined;
    }

    return jQuery.ajax({
        url: url,
        type: "POST",
        contentType:"application/json",
        dataType: "json",
        data: JSON.stringify(data),
        success: callback
    });
};

var GarageButton = React.createClass({
  handleClick: function(){
    console.log("garage clicked");
    $.post(postUrl,"").done(function(x) {
        console.log("garage click success");
    }).fail(function(){
      console.log("garage click fail");
      alert("button broken!");
    });
  },
  render: function() {
    return (
      <div className="round-button">
        <div className="round-button-circle">
          <button id="button" className="pure-round center"
            onClick={this.handleClick}>
            { this.props.garage_open ? "CLOSE" : "OPEN"}
          </button>
        </div>
      </div>
    );
  }
});

var StatusDisplay = React.createClass({
  render: function() {
    return (
      <div>
      <div className="pure-g">
        <div className="pure-u-1-4"></div>
        <div className="pure-u-1-4 tcenter">
          { this.props.garage_open ? "CLOSED" : "OPEN"} for:
        </div>
        <div className="pure-u-1-4">
          <div className="l-box">{this.props.last_change}</div>
        </div>
        <div className="pure-u-1-4"></div>
      </div>
      <div className="pure-g">
        <div className="pure-u-1-4"></div>
        <div className="pure-u-1-4 tcenter ">
          Last Motion:
        </div>
        <div className="pure-u-1-4">
          <div className="l-box">{this.props.last_motion}</div>
        </div>
        <div className="pure-u-1-4"></div>
      </div>
      </div>
    );
  }
});

var GarageImage = React.createClass({
  getInitialState: function() {
    return {
      image_src: "http://admin:taco@10.10.10.102/image/jpeg.cgi"
    };
  },
  componentDidMount: function() {
    // setInterval(this.handleClick, 5000);
  },
  handleClick: function() {
    var d = new Date();
    this.setState({ image_src: "http://admin:taco@10.10.10.102/image/jpeg.cgi"+d.getTime() })
  },
  render: function() {
    return (
      <div>
        <img className="center" src={this.state.image_src}
          onClick={this.handleClick} />
      </div>
    );
  }
});

var ControlButtons = React.createClass({
  handleLockClick: function() {
    console.log("lock click");
    $.postJSON(lockUrl, { locked: !this.props.locked },
      function(data) {
        console.log(data);
        // $("#lock").attr("data-locked", data.locked);
        // todo: update locked icon instantly?
      });
  },
  handlePirClick: function() {
    console.log("pir click");
    $.postJSON(pirUrl, { enabled: !this.props.pir_enabled },
      function(data) {
        console.log(data);
        // $("#pir").attr("data-pir-enabled", data.pir_enabled);
      });
  },
  handleDweetClick: function() {
    console.log("dweet click");
    $.postJSON(dweetUrl, { enabled: !this.props.dweet_enabled },
      function(data) {
        console.log(data);
        // $("#dweet").attr("data-dweet-enabled", data.dweet_enabled);
      });
  },
  render: function() {
    var dweet;
    if (this.props.dweet_enabled) {
      dweet = <i className="fa fa-whatsapp"></i>;
    } else {
      dweet = <span className="fa-stack">
                <i className="fa fa-whatsapp fa-stack-1x"></i>
                <i className="fa fa-ban fa-stack-1x"></i>
              </span>;
    }
    return (
      <div className="pure-g">
      <div className='pure-u-1-3 tcenter'>
        <button className="pure-button"
          onClick={this.handleLockClick}>
          <i className={this.props.locked ? "fa fa-lock" : "fa fa-unlock"}></i>
          &nbsp; LOK
        </button>
      </div>
      <div className='pure-u-1-3 tcenter'>
        <button className="pure-button"
          onClick={this.handlePirClick}>
          <i className={this.props.pir_enabled ? "fa fa-eye" : "fa fa-eye-slash" }></i>
          &nbsp;PIR
        </button>
      </div>
      <div className='pure-u-1-3 tcenter'>
        <button className="pure-button"
          onClick={this.handleDweetClick}>
          {dweet}
          &nbsp;dweet
        </button>
      </div>
    </div>
    );
  }
});

var Garage = React.createClass({
  getInitialState: function(){
    return {
      garage_open: true,
      last_change: 0,
      last_motion: 0,
      dweet_enabled: true,
      pir_enabled: true,
      locked: false
    }
  },
  componentDidMount: function(){
    var eventSource = new EventSource(listenUrl);
    eventSource.onmessage = function (e) {
        this.updateState(JSON.parse(e.data));
        $("#log").html(e.data);
    }.bind(this);
  },
  updateState: function(data) {
    this.setState({
      garage_open: data.mag,
      last_change: data.times.last_mag,
      last_motion: data.times.last_pir,
      dweet_enabled: data.dweet_enabled,
      pir_enabled: data.pir_enabled,
      locked: data.locked
    })
  },
  render: function() {
    return (
      <div>
      <GarageButton
        garage_open={this.state.garage_open} />
      <StatusDisplay
        garage_open={this.state.garage_open}
        last_change={this.state.last_change}
        last_motion={this.state.last_motion} />
      <ControlButtons
        dweet_enabled={this.state.dweet_enabled}
        pir_enabled={this.state.pir_enabled}
        locked={this.state.locked}/>
      <GarageImage />
      </div>
    );
  }
})

React.render(
  <Garage />,
  document.getElementById("content")
);
