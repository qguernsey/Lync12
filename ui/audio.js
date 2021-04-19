/* global $: false */

/* jshint -W097 */
'use strict';

function disable(elem, yes) {
  if (yes) {
    //elem.removeAttr('disabled');
  } else {
    //elem.attr('disabled', 'disabled');
  }
}

var audio = {
  state: {},
  boundEvents: false,
  desiredVolume: -1 ,
  updateState: function(state) {
    for (var i in state) {
      this.state[i] = state[i];
     /* Passing from the status controller now this.state[i].name = this.zoneNames[i]; */
    }
    this.sync(Object.keys(state));
  },
  _getZone: function(e) {
    return e.name.split(/-/)[1];
  },
  changePower: function(event) {
    var zone = this._getZone(event.target);
    var value = event.target.value == 'on' ? 1 : 0;
    value = {power: value};
    console.log('power', value);

    $.ajax({
      url: 'http://'+window.location.hostname+':8080/zone/'+zone+'/power',
      type: 'PUT',
      data: value
    }).done(function(data) {
      audio.updateState(data);
    });
  },
  changeMute: function(event) {
    console.log('Mute')
    var that = this;
    var zone = this._getZone(event.target);
    var value = event.target.value == 'on' ? 1 : 0;
    value = {mute: value};
    console.log('mute', value);
    $.ajax({
      url: 'http://'+window.location.hostname+':8080/zone/'+zone+'/mute',
      type: 'PUT',
      data: value
    }).done(function(data) {
      audio.updateState(data);
    });
  },
  changeVolume: function(event) {
    var that = this;
    //only change the volume if we haven't had a change in the last 500ms
    var zone = that._getZone(event.target);
    that.disableVolume(zone);
    $.ajax({
      url: 'http://'+window.location.hostname+':8080/zone/'+zone+'/volume',
      type: 'PUT',
      data: {volume: event.target.value}
    }).done(function(data) {
      that.enableVolume(zone);
      audio.updateState(data);
    });
  },
    changeBalance: function(event) {
    var that = this;
    //only change the balance if we haven't had a change in the last 500ms
    var zone = that._getZone(event.target);
    that.disableBalance(zone);
    $.ajax({
      url: 'http://'+window.location.hostname+':8080/zone/'+zone+'/balance',
      type: 'PUT',
      data: {balance: event.target.value}
    }).done(function(data) {
      that.enableBalance(zone);
      audio.updateState(data);
    });
  },
    changeBass: function(event) {
    var that = this;
    //only change the balance if we haven't had a change in the last 500ms
    var zone = that._getZone(event.target);
    that.disableBass(zone);
    $.ajax({
      url: 'http://'+window.location.hostname+':8080/zone/'+zone+'/bass',
      type: 'PUT',
      data: {bass: event.target.value}
    }).done(function(data) {
      that.enableBass(zone);
      audio.updateState(data);
    });
  },
    changeTreble: function(event) {
    var that = this;
    //only change the balance if we haven't had a change in the last 500ms
    var zone = that._getZone(event.target);
    that.disableTreble(zone);
    $.ajax({
      url: 'http://'+window.location.hostname+':8080/zone/'+zone+'/treble',
      type: 'PUT',
      data: {treble: event.target.value}
    }).done(function(data) {
      that.enableTreble(zone);
      audio.updateState(data);
    });
  },

  changeInput: function(event) {
    console.log('input', arguments);
    var zone = this._getZone(event.target);
    $.ajax({
      url: 'http://'+window.location.hostname+':8080/zone/'+zone+'/input',
      type: 'PUT',
      data: {input: event.target.value}
    }).done(function(data) {
      audio.updateState(data);
    });
  },
    changeMP3: function(event) {
    console.log('input', arguments);
    console.log('value', event.target)
    var value = event.target.value;
    $.ajax({
      url: 'http://'+window.location.hostname+':8080/mp3/'+value,
      type: 'PUT',
      data: {input: event.target.value}
    }).done(function(data) {
      audio.updateState(data);
    });
  },
  bindEvents: function() {
    this.boundEvents = true;
    $('.muteContainer').on('change', this.changeMute.bind(this));
    $('.powerContainer').on('change', this.changePower.bind(this));
    $('.volumeSlider').on('slidestop', this.changeVolume.bind(this));
    $('.balanceSlider').on('slidestop', this.changeBalance.bind(this));
    $('.bassSlider').on('slidestop', this.changeBass.bind(this));
    $('.trebleSlider').on('slidestop', this.changeTreble.bind(this));
    $('select').on('change', this.changeInput.bind(this));
    $('#globalSettings').click(function(){
        $('#globalSettingsModal').modal({backdrop: 'static'});
    });
    $('#settings-1').click(function(){
        $('#settingsModal-1').modal({backdrop: 'static'});
    });
    $('#settings-2').click(function(){
        $('#settingsModal-2').modal({backdrop: 'static'});
    });
    $('#settings-3').click(function(){
        $('#settingsModal-3').modal({backdrop: 'static'});
    });
    $('#settings-4').click(function(){
        $('#settingsModal-4').modal({backdrop: 'static'});
    });
    $('#settings-5').click(function(){
        $('#settingsModal-5').modal({backdrop: 'static'});
    });
    $('#settings-6').click(function(){
        $('#settingsModal-6').modal({backdrop: 'static'});
    });
    $('#settings-7').click(function(){
        $('#settingsModal-7').modal({backdrop: 'static'});
    });
    $('#settings-8').click(function(){
        $('#settingsModal-8').modal({backdrop: 'static'});
    });
    $('#settings-9').click(function(){
        $('#settingsModal-9').modal({backdrop: 'static'});
    });
    $('#settings-10').click(function(){
        $('#settingsModal-10').modal({backdrop: 'static'});
    });
    $('#settings-11').click(function(){
        $('#settingsModal-11').modal({backdrop: 'static'});
    });
    $('#settings-12').click(function(){
        $('#settingsModal-12').modal({backdrop: 'static'});
    });
    $('.mp3-player').bind('click', this.changeMP3.bind(this));
  },
  disableVolume: function(zoneId) {
    console.log("disable", zoneId);
    $('#volume-'+zoneId).slider('disable').slider('refresh');
  },
  enableVolume: function(zoneId) {
    console.log("enable", zoneId);
    $('#volume-'+zoneId).slider('enable').slider('refresh');
  },
  disableBalance: function(zoneId) {
    console.log("disable", zoneId);
    $('#balance-'+zoneId).slider('disable').slider('refresh');
  },
  enableBalance: function(zoneId) {
    console.log("enable", zoneId);
    $('#balance-'+zoneId).slider('enable').slider('refresh');
  },
  disableTreble: function(zoneId) {
    console.log("disable", zoneId);
    $('#treble-'+zoneId).slider('disable').slider('refresh');
  },
  enableTreble: function(zoneId) {
    console.log("enable", zoneId);
    $('#treble-'+zoneId).slider('enable').slider('refresh');
  },
   disableBass: function(zoneId) {
    console.log("disable", zoneId);
    $('#bass-'+zoneId).slider('disable').slider('refresh');
  },
  enableBass: function(zoneId) {
    console.log("enable", zoneId);
    $('#bass-'+zoneId).slider('enable').slider('refresh');
  },
  sync: function(zoneIds) {
    if (!this.boundEvents) {
      this.bindEvents();
    }
    for (var i in this.state) {
      if (zoneIds.indexOf(i) == -1) {
        continue;
      }
      var s = this.state[i];
      console.log('updating', i, s);
      if (s.power) {
        $('#zone-'+i).addClass('on');
        $('#zone-'+i).removeClass('off');
      } else {
        $('#zone-'+i).addClass('off');
        $('#zone-'+i).removeClass('on');
      }
      var enabled = s.power ? 'enable' : 'disable';
      $('#title-'+i).html(s.name);
      if (s.power) {
        $('#power-'+i+'-on').prop('checked', true).checkboxradio('refresh');
        $('#power-'+i+'-off').prop('checked', false).checkboxradio('refresh');
         $('#settings-'+i).prop('disabled', false).button('refresh');
      } else {
        $('#power-'+i+'-on').prop('checked', false).checkboxradio('refresh');
        $('#power-'+i+'-off').prop('checked', true).checkboxradio('refresh');
        $('#settings-'+i).prop('disabled', true).button('refresh');
      }
      $.each(s.inputs, function(key, value) {
         $('#input-'+i)
           .append($("<option></option>")
           .attr("value",key)
           .text(value));
          });
      $('#input-'+i)[0].selectedIndex = s.input - 1;
      $('#input-'+i).selectmenu(enabled).selectmenu('refresh');


      $('#volume-'+i).val(s.volume).slider(enabled).slider('refresh');
      $('#balance-'+i).val(s.balance).slider(enabled).slider('refresh');
      $('#treble-'+i).val(s.treble).slider(enabled).slider('refresh');
      $('#bass-'+i).val(s.bass).slider(enabled).slider('refresh');

    }
  }
};

$.ajax({
  url: 'http://'+window.location.hostname+':8080/status'
}).done(function(data) {
  audio.updateState(data);
});
