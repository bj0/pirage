/*** @jsx React.DOM */

var postUrl = "/click";
var listenUrl = "/stream";
var lockUrl = "/set_lock";
var pirUrl = "/set_pir";
var dweetUrl = "/set_dweet"

// add postJSON alias function for ajax call pushing json
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

// big open/close garage button
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
      <button id="button" className="pure-button pure-round center"
        onClick={this.handleClick}>
        { this.props.garage_open ? "CLOSE" : "OPEN"}
      </button>
    );
  }
});

// displays current garage status
var StatusDisplay = React.createClass({
  render: function() {
    return (
      <table className="pure-table" style={{marginTop: '20px'}}>
        <tbody>
          <tr>
            <td>{ this.props.garage_open ? "open" : "closed" } for:</td>
            <td>{this.props.last_change}</td>
          </tr>
          <tr>
            <td>last motion:</td>
            <td>{this.props.last_motion}</td>
          </tr>
          <tr>
            <td>temp:</td>
            <td>{this.props.temperature} &deg;C</td>
          </tr>
        </tbody>
      </table>
    );
  }
});

// displays camera image
var GarageImage = React.createClass({
  getInitialState: function() {
    return {
      image_src: "http://admin:taco@10.10.10.102/image/jpeg.cgi",
      altimage_src: "/static/images/loading.png",
      loaded: false
    };
  },
  // componentDidMount: function() {
  //   // we can periodically update the image here
  //   setInterval(this.handleClick, 5000);
  // },
  handleClick: function() {
    var url = "http://admin:taco@10.10.10.102/image/jpeg.cgi?"+Date.now();
    console.log(url);
    this.setState({ image_src: url })
  },
  handleError: function() {
    // called when image fails to load
    console.log("cannot get image from webcam");
    this.setState({ altimage_src: "/static/images/fail.png"});
  },
  handleLoad: function() {
    // called when image is loaded
    this.setState({ loaded: true });
  },
  render: function() {
    return (
      <div style={{margin: '10px'}}>
        <img className="center" src={this.state.image_src} hidden={ !this.state.loaded }
          onLoad={this.handleLoad}
          onError={this.handleError}
          onClick={this.handleClick} />
        <img className="center" src={this.state.altimage_src} hidden={ this.state.loaded }
          onClick={this.handleClick}/>
      </div>
    );
  }
});

// toggle buttons for controlling features
var DweetButton = React.createClass({
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
      <button className="pure-button fa-button"
        onClick={this.props.handleDweetClick}>
        {dweet}
      </button>
    )
  }
});

var LockButton = React.createClass({
  render: function() {
    return (
      <button className="pure-button fa-button"
        onClick={this.props.handleLockClick}>
        <i className={this.props.locked ? "fa fa-lock" : "fa fa-unlock"}></i>
      </button>
    )
  }
});

var PirButton = React.createClass({
  render: function() {
    return (
      <button className="pure-button fa-button"
        onClick={this.props.handlePirClick}>
        <i className={this.props.pir_enabled ? "fa fa-eye" : "fa fa-eye-slash" }></i>
      </button>
    )
  }
});

var ControlButtons = React.createClass({
  render: function() {
    return (
      <div style={{textAlign:'right', marginTop: '10px'}}>
        <LockButton {...this.props}/><br/>
        <PirButton {...this.props} /><br/>
        <DweetButton {...this.props}/>
      </div>
    //   <div className="pure-g">
    //   <div className='pure-u-1-3 tcenter'>
    //     <LockButton {...this.props}/>
    //   </div>
    //   <div className='pure-u-1-3 tcenter'>
    //     <PirButton {...this.props} />
    //   </div>
    //   <div className='pure-u-1-3 tcenter'>
    //     <DweetButton {...this.props}/>
    //   </div>
    // </div>
    );
  }
});

// container for everything
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
        this.setState({log:e.data});
    }.bind(this);
  },
  updateState: function(data) {
    this.setState({
      garage_open: data.mag,
      last_change: data.times.last_mag,
      last_motion: data.times.last_pir,
      dweet_enabled: data.dweet_enabled,
      pir_enabled: data.pir_enabled,
      locked: data.locked,
      temperature: data.temp,
      log: "hi"
    })
  },
  handleLockClick: function() {
    console.log("lock click");
    $.postJSON(lockUrl, { locked: !this.state.locked },
      function(data) {
        console.log(data);
        this.setState({ locked: data.locked })
      }.bind(this));
  },
  handlePirClick: function() {
    console.log("pir click");
    $.postJSON(pirUrl, { enabled: !this.state.pir_enabled },
      function(data) {
        console.log(data);
        this.setState({ pir_enabled: data.pir_enabled })
      }.bind(this));
  },
  handleDweetClick: function() {
    console.log("dweet click");
    $.postJSON(dweetUrl, { enabled: !this.state.dweet_enabled },
      function(data) {
        console.log(data);
        this.setState({ dweet_enabled: data.dweet_enabled });
      }.bind(this));
  },
  render: function() {
    return (
      <div>
        <div className="pure-g">
          <div className="pure-u-1-3">
            <ControlButtons
              dweet_enabled={this.state.dweet_enabled}
              pir_enabled={this.state.pir_enabled}
              locked={this.state.locked}
              handlePirClick={this.handlePirClick}
              handleDweetClick={this.handleDweetClick}
              handleLockClick={this.handleLockClick} />
          </div>
          <div className="pure-u-1-3">
          <GarageImage />
          </div>
          <div className="pure-u-1-3">
          <StatusDisplay
            garage_open={this.state.garage_open}
            last_change={this.state.last_change}
            last_motion={this.state.last_motion}
            temperature={this.state.temperature} />
        </div>
        </div>
      <GarageButton
        garage_open={this.state.garage_open} />
      <div id="log" style={{fontFamily: 'courier', fontSize: '0.75em' }}>{this.state.log}</div>
      </div>
    );
  }
})

React.render(
  <Garage />,
  document.getElementById("content")
);