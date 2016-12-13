// main.jsx

var Button = ReactBootstrap.Button;
var ButtonGroup = ReactBootstrap.ButtonGroup;
var Grid = ReactBootstrap.Grid;
var Row = ReactBootstrap.Row;
var Col = ReactBootstrap.Col;
var Table = ReactBootstrap.Table;
var Image = ReactBootstrap.Image;

var postUrl = "/click";
var listenUrl = "/stream";
var lockUrl = "/set_lock";
var pirUrl = "/set_pir";
var notifyUrl = "/set_notify"

// add postJSON alias function for ajax call pushing json
jQuery["postJSON"] = function(url, data, callback) {
    // shift arguments if data argument was omitted
    if (jQuery.isFunction(data)) {
        callback = data;
        data = undefined;
    }

    return jQuery.ajax({
        url: url,
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(data),
        success: callback
    });
};

// big open/close garage button
var GarageButton = React.createClass({
    handleClick: function() {
        console.log("garage clicked");
        $.post(postUrl, "").done(function(x) {
            console.log("garage click success");
        }).fail(function() {
            console.log("garage click fail");
            alert("button broken!");
        });
    },
    render: function() {
        return (
            <Button bsStyle="success" block onClick={this.handleClick}>
                { this.props.garage_open ? "CLOSE" : "OPEN"}
            </Button>
        );
    }
});

var GetImageButton = React.createClass({
    render: function() {
        return (
            <Button bsStyle="success" block
                onClick={this.props.handleClick}>
                GET IMAGE
            </Button>
        );
    }
});

// displays current garage status
var StatusDisplay = React.createClass({
    render: function() {
        return (
            <Table striped bordered condensed hover>
                <tbody>
                    <tr>
                        <td>{ this.props.garage_open ? "open" : "closed" } for: </td>
                        <td>{this.props.last_change}</td>
                    </tr>
                    <tr>
                        <td>last motion: </td>
                        <td>{this.props.last_motion}</td>
                    </tr>
                    <tr>
                        <td>temp: </td>
                        <td>{this.props.temperature} &deg; C</td>
                    </tr>
                </tbody>
            </Table>
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
        if (this.state.loaded && this.props.ai_enabled) {
            var url = "/cam/image?" + Date.now();
            this.setState({ image_src: url });
        }
    },
    handleClick: function() {
        var url = "/cam/image?" + Date.now();
        console.log(url);
        this.setState({ image_src: url, altimage_src: "/static/images/loading.png", loaded: false });
    },
    handleError: function() {
        // called when image fails to load
        console.log("cannot get image from webcam");
        this.setState({ altimage_src: "/static/images/fail.png", loaded: false });
    },
    handleLoad: function() {
        // called when image is loaded
        console.log("loaded");
        this.setState({ loaded: true });
    },
    render: function() {
        return (
            <div style={{ margin: '10px' }}>
                <Image className={"center " + (this.state.loaded ? null : "hidden") } src={this.state.image_src}
                    responsive
                    onLoad={this.handleLoad}
                    onError={this.handleError}
                    onClick={this.handleClick} />
                <Image className={"center " + (this.state.loaded ? "hidden" : null) } src={this.state.altimage_src}
                    responsive
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
                <i className="fa fa-ban fa-stack-2x"></i>
            </span>;
        }
        return (
            <Button className="pad"
                onClick={this.props.handleNotifyClick}>
                {notify}
            </Button>
        )
    }
});

var LockButton = React.createClass({
    render: function() {
        return (
            <Button className="pad"
                onClick={this.props.handleLockClick}>
                <i className={this.props.locked ? "fa fa-lock" : "fa fa-unlock"}></i>
            </Button>
        )
    }
});

var PirButton = React.createClass({
    render: function() {
        return (
            <Button className="pad"
                onClick={this.props.handlePirClick}>
                <i className={this.props.pir_enabled ? "fa fa-eye" : "fa fa-eye-slash" }></i>
            </Button>
        )
    }
});

var AutoImageButton = React.createClass({
    render: function() {
        var img;
        if (this.props.ai_enabled) {
            img = <i className="fa fa-picture-o"></i>;
        } else {
            img = <span className="fa-stack">
                <i className="fa fa-picture-o fa-stack-1x"></i>
                <i className="fa fa-ban fa-stack-2x"></i>
            </span>;
        }
        return (
            <Button className="pad"
                onClick={this.props.handleAutoImageClick}>
                {img}
            </Button>
        )
    }
})

var ControlButtons = React.createClass({
    render: function() {

        var style;
        if (this.props.dock)
            style = {}
        else
            style = { textAlign: 'right', marginTop: '10px', float: 'right' }

        return (
            <div className="text-center">
                <ButtonGroup style={style} vertical={!this.props.dock}>
                    <LockButton {...this.props}/>
                    <PirButton {...this.props} />
                    <NotifyButton {...this.props}/>
                    <AutoImageButton {...this.props}/>
                </ButtonGroup>
            </div>
        );
    }
});

// container for everything
var Garage = React.createClass({
    getInitialState: function() {
        return {
            garage_open: true,
            last_change: 0,
            last_motion: 0,
            notify_enabled: true,
            pir_enabled: true,
            ai_enabled: true,
            locked: false,

            dock: false
        }
    },
    componentDidMount: function() {
        // setup eventsource
        var eventSource = new EventSource(listenUrl);
        eventSource.onmessage = function(e) {
            console.log("message");
            this.updateState(JSON.parse(e.data));
            this.setState({ log: e.data });
        }.bind(this);
        eventSource.onerror = function(e) { console.log("err:" + e); }

        // get permission to send notifications
        if ("Notification" in window)
            Notification.requestPermission();

        // add media query callback
        var mq = window.matchMedia("(min-width: 768px)");
        mq.addListener(this.mqChange);
        this.setState({ dock: !mq.matches });
    },
    mqChange: function(mq) {
        this.setState({ dock: !mq.matches });
    },
    updateState: function(data) {

        // check if garage changed, send notification to desktop
        if (this.state.garage_open !== data.mag) {
            console.log("garage changed:", this.state.garage_open, "->", data.mag);
            if ("Notification" in window
                && Notification.permission === "granted"
                && this.state.notify_enabled)
                new Notification("Garage " + (data.mag ? "Open!" : "Closed!"));
        }

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
    handleAutoImageClick: function() {
        var new_state = !this.state.ai_enabled;
        if (new_state)
            this.handleGetImageClick();
        this.setState({ ai_enabled: new_state });
    },
    handleGetImageClick: function() {
        this.refs['image'].handleClick();
    },
    render: function() {

        var center = (
            <Row>
                <Col>
                    <GarageButton
                        garage_open={this.state.garage_open} />
                </Col>
                <Col>
                    <GarageImage ref="image"
                        ai_enabled={this.state.ai_enabled}/>
                </Col>
                <Col>
                    <GetImageButton
                        handleClick={this.handleGetImageClick} />
                </Col>
            </Row>
        );

        return (
            <Grid>
                <Row>
                    <Col xs={12} sm={2}>
                        <ControlButtons
                            dock={this.state.dock}
                            notify_enabled={this.state.notify_enabled}
                            pir_enabled={this.state.pir_enabled}
                            locked={this.state.locked}
                            ai_enabled={this.state.ai_enabled}
                            handlePirClick={this.handlePirClick}
                            handleNotifyClick={this.handleNotifyClick}
                            handleLockClick={this.handleLockClick}
                            handleAutoImageClick={this.handleAutoImageClick} />
                    </Col>
                    <Col xs={12} sm={6}>
                        {center}
                    </Col>
                    <Col xs={12} sm={4}>
                        <StatusDisplay
                            garage_open={this.state.garage_open}
                            last_change={this.state.last_change}
                            last_motion={this.state.last_motion}
                            temperature={this.state.temperature} />
                    </Col>
                </Row>
                <div id="log" style={{ fontFamily: 'courier', fontSize: '0.75em' }}>{this.state.log}</div>
            </Grid>
        );
    }
})

ReactDOM.render(
    <Garage />,
    document.getElementById("content")
);
