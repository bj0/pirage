/*** @jsx React.DOM */

var postUrl = "/click";
var listenUrl = "/stream";
var lockUrl = "/set_lock";
var pirUrl = "/set_pir";
var notifyUrl = "/set_notify"

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
      <table className="pure-table">
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
      image_src: "/cam/image",
      altimage_src: "/static/images/loading.png",
      loaded: false
    };
  },
  componentDidMount: function() {
    // we can periodically update the image here
    setInterval(this.updateTick, 10000);
  },
  updateTick: function() {
    if( this.state.loaded )
      this.handleClick();
  },
  handleClick: function() {
    var url = "/cam/image?"+Date.now();
    console.log(url);
    if( this.state.loaded )
        this.setState({ image_src: url });
    else
        this.setState({ image_src: url, altimage_src: "/static/images/loading.png"});
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
          width="320" height="240"
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
var NotifyButton = React.createClass({
  render: function() {
    var notify;
    if (this.props.notify_enabled) {
      notify = <i className="fa fa-whatsapp"></i>;
    } else {
      notify = <span className="fa-stack">
                <i className="fa fa-whatsapp fa-stack-1x"></i>
                <i className="fa fa-ban fa-stack-1x"></i>
              </span>;
    }
    return (
      <button className="pure-button fa-button"
        onClick={this.props.handleNotifyClick}>
        {notify}
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
        <NotifyButton {...this.props}/>
      </div>
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
      notify_enabled: true,
      pir_enabled: true,
      locked: false
    }
  },
  componentDidMount: function(){
    console.log("eventsource");
    var eventSource = new EventSource(listenUrl);
    eventSource.onmessage = function (e) {
        console.log("message");
        this.updateState(JSON.parse(e.data));
        this.setState({log:e.data});
    }.bind(this);
    eventSource.onerror = function (e) { console.log("err:"+e); }
  },
  updateState: function(data) {
    this.setState({
      garage_open: data.mag,
      last_change: data.times.last_mag,
      last_motion: data.times.last_pir,
      notify_enabled: data.notify_enabled,
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
  handleNotifyClick: function() {
    console.log("notify click");
    $.postJSON(notifyUrl, { enabled: !this.state.notify_enabled },
      function(data) {
        console.log(data);
        this.setState({ notify_enabled: data.notify_enabled });
      }.bind(this));
  },
  render: function() {
    return (
      <div>
        <div className="pure-g">
          <div className="pure-u-1-5">
            <ControlButtons
              notify_enabled={this.state.notify_enabled}
              pir_enabled={this.state.pir_enabled}
              locked={this.state.locked}
              handlePirClick={this.handlePirClick}
              handleNotifyClick={this.handleNotifyClick}
              handleLockClick={this.handleLockClick} />
          </div>
          <div className="pure-u-2-5">
          <GarageImage />
          </div>
          <div className="pure-u-2-5">
          <StatusDisplay
            garage_open={this.state.garage_open}
            last_change={this.state.last_change}
            last_motion={this.state.last_motion}
            temperature={this.state.temperature} />
        </div>
        </div>
        <div className="pure-g">
          <div className="pure-u-1-5"/>
          <div className="pure-u-2-5">
          <GarageButton
            garage_open={this.state.garage_open} />
          </div>
      </div>
      <div id="log" style={{fontFamily: 'courier', fontSize: '0.75em' }}>{this.state.log}</div>
      </div>
    );
  }
})

React.render(
  <Garage />,
  document.getElementById("content")
);
