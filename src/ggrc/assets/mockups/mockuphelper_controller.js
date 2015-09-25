/*!
    Copyright (C) 2015 Google Inc., authors, and contributors <see AUTHORS file>
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
    Created By: anze@reciprocitylabs.com
    Maintained By: anze@reciprocitylabs.com
*/


(function (can, $) {
  can.route(":tab", {tab: "Info"});
  can.route(":tab/:item");

  // Activate router
  $(document).ready(can.route.ready);

  can.Control("CMS.Controllers.MockupHelper", {
    defaults: {
      title_view: GGRC.mustache_path + "/title.mustache",
      object_views: {}
    }
  }, {
    init: function (el, opts) {
      var views = new can.List(this.options.views),
          options = {
            views: views
          };
      new CMS.Controllers.MockupNav(this.element.find(".internav"), options);
      new CMS.Controllers.MockupView(this.element.find(".inner-content"), options);
      new CMS.Controllers.MockupInfoPanel(this.element.find(".info-pin"), options);

      this.element.find(".title-content").html(can.view(this.options.title_view, opts.object));
      this.options.views = views;
    },
    "{can.route} tab": function (router, ev, tab) {
      _.each(this.options.views, function (view) {
        view.active = view.title === tab;
      });
    }
  });

  can.Control("CMS.Controllers.MockupNav", {
    defaults: {
      view: "/static/mockups/base_templates/nav_item.mustache"
    }
  }, {
    "{can.route} tab": function () {
      this.element.html(can.view(this.options.view, this.options));
    }
  });

  can.Control("CMS.Controllers.MockupView", {
    defaults: {
      title_view: GGRC.mustache_path + "/title.mustache"
    }
  }, {
    "{can.route} tab": function () {
      var view = _.findWhere(this.options.views, {active: true});
      this.element.html(can.view(GGRC.mustache_path + view.template));
      if (view.children) {
        new CMS.Controllers.MockupTreeView(this.element.find(".base-tree-view"), view);
      }
    }
  });

  can.Control("CMS.Controllers.MockupTreeView", {
  }, {
    init: function (el, opts) {
      _.each(this.options.children, function (child) {
        var $item = $("<li/>", {class: "tree-item"});
        new CMS.Controllers.MockupTreeItem($item, {
          item: child
        });
        this.element.append($item);
      }, this);
    },
    "{can.route} item": function (router, ev, item) {
      if (!item || !item.length) {
        return;
      }
      item = item.split("-");
      var view = _.findWhere(this.options.children, {
            type: item[0],
            id: item[1]
          });
      view.attr("active", true);
    },
    "{children} change": function (list, ev, which, type, status) {
      which = which.split(".");
      var index = +which[0],
          prop = which[1];

      if (!status) {
        return;
      }
      _.each(this.options.children, function (child, i) {
        var isActive = index === i;
        child.attr("active", isActive);
        if (isActive) {
          can.route.attr("item", child.type + "-" + child.id);
        }
      });
    }
  });

  can.Control("CMS.Controllers.MockupTreeItem", {
    defaults: {
      view: "/static/mockups/base_templates/tree_item.mustache"
    }
  }, {
    init: function (el, options) {
      this.element.html(can.view(this.options.view, options.item));
    },
    ".select click": function (el, ev) {
      var status = !this.options.item.active;
      this.options.item.attr("active", status);
    },
    "{item} change": function (list, ev, which, type, status) {
      this.element.toggleClass("active", status);
    }
  });


  can.Control("CMS.Controllers.MockupInfoPanel", {
    defaults: {
      view: "/static/mockups/base_templates/info_panel.mustache",
      slide: 240
    }
  }, {
    ".pin-action a click": function (el, ev) {
      var size = el.data("size"),
          height = Math.round($(window).height() / 3),
          heights = {
            deselect: 0,
            min: height,
            normal: height*2,
            max: height*3
          };

      el.find("i").css("opacity", 1).closest("li").siblings().find("i").css("opacity", 0.25);
      this.element
        .show()
        .animate({
          height: heights[size]
        }, {
          duration: this.options.slide,
          complete: function () {
            if (size === "deselect") {
              this.element.hide();
              this.active.attr("active", false);
              can.route.removeAttr("item");
            }
          }.bind(this)
        });
    },
    "{can.route} item": function (router, ev, item) {
      // TODO: Simplify this
      if (!item || !item.length) {
        return;
      }
      function recursiveFind(needle) {
        if (needle.type === item[0] && needle.id === item[1]) {
          return needle;
        }
        if (needle.children && needle.children.length) {
          return _.map(needle.children, recursiveFind);
        }
      }
      item = item.split("-");
      var view = _.compact(_.flattenDeep(_.map(this.options.views, recursiveFind)))[0];
      this.active = view;
      this.element.html(can.view(this.options.view, view));
      this.element.show();
    }
  });
})(this.can, this.can.$);
