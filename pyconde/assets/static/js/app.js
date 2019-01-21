(function(doc, win) {
  "use strict";

  /**
   * @see https://github.com/hesambayat/is-touch-device-javascript
   */
  var istouch = "undefined" !== IS_TOUCH_DEVICE && IS_TOUCH_DEVICE ? true : false;

  var isMac = false;

  /**
   * @see https://stackoverflow.com/a/38241481/2131534
   */
  try {
    if (["Macintosh", "MacIntel", "MacPPC", "Mac68K"].indexOf(win.navigator.platform) !== -1) {
      isMac = true;
    }
  } catch (error) {}

  var isChrome = false;

  /**
   * @see https://stackoverflow.com/a/9851769/2131534
   */
  try {
    isChrome = !!window.chrome && !!window.chrome.webstore;
  } catch (error) {}

  /**
   * PaperJS patterns will give your site a colorful and playful look,
   * Users will enjoy to spend more time in the website.
   */
  function pixudio_paper() {
    // paper has not included.
    if ("undefined" === typeof paper) return;

    doc.querySelectorAll(".paper--patterns").forEach(function(parent) {
      var canvas = parent.querySelector("canvas"),
        config = win[parent.getAttribute("data-elements")],
        scope = new paper.PaperScope();

      scope.setup(canvas);
      scope.view.viewSize.width = canvas.clientWidth;
      scope.view.viewSize.height = canvas.clientHeight;

      var tools = new scope.Tool(),
        drawing = false,
        pageScrolling = false,
        display = "desktop",
        viewport = {},
        mouse = {
          x: 0,
          y: 0,
          limit: 0.2,
          speed: 0.00015,
          onmove: false
        },
        tilt = {
          min: 40,
          max: -40,
          speed: 0.002,
          angle: 0,
          direction: 1
        },
        setting = {
          deltaX: 0,
          deltaY: 0
        },
        group;

      // animations

      // mouse move animation
      var mouseMove = function(event) {
        // pause on page scroll
        if (false !== pageScrolling) {
          return;
        }

        // pause if meshes aren’t out there yet
        if (undefined === group || undefined === group.children) {
          return;
        }

        for (var i = 0, len = group.children.length; i < len; i++) {
          // set new x axis if its in limited radius
          setting.deltaX = group.children[i].position.x + (mouse.x - viewport.x) * ((i + 1) * mouse.speed);
          if (setting.deltaX > group.children[i].limits.x.min && setting.deltaX < group.children[i].limits.x.max) {
            group.children[i].position.x = setting.deltaX;
          }

          // set new y axis if its in limited radius
          setting.deltaY = group.children[i].position.y + (mouse.y - viewport.y) * ((i + 1) * mouse.speed);
          if (setting.deltaY > group.children[i].limits.y.min && setting.deltaY < group.children[i].limits.y.max) {
            group.children[i].position.y = setting.deltaY;
          }
        }
      };

      // auto tilt animation
      var tiltMove = function(event) {
        // pause on page scroll
        if (false !== pageScrolling) {
          return;
        }

        // to move up or down
        if (tilt.angle > tilt.min) {
          tilt.direction = -1;
        } else if (tilt.angle < tilt.max) {
          tilt.direction = 1;
        }

        // Move once step ahead
        tilt.angle += tilt.direction;
        // set Y axis
        for (var i = 0, len = group.children.length; i < len; i++) {
          group.children[i].position.y += tilt.angle * tilt.speed * (i + 1);
        }
      };

      // helpers

      // shorten for paper.Point
      var point = function(axis, y) {
        if (undefined !== y) {
          axis = {
            x: axis,
            y: y
          };
        }
        return new scope.Point(axis.x, axis.y);
      };

      // get coordinates from center
      var getCoordinates = function(axis) {
        return {
          x: viewport.x + axis[display].x,
          y: viewport.y + axis[display].y
        };
      };

      // transform to a point
      var translate = function(axis) {
        return point(getCoordinates(axis));
      };

      // recognize display size & draw
      var update = function() {
        if (false !== drawing) {
          return;
        }

        drawing = true;

        scope.view.onFrame = null;
        scope.project.activeLayer.removeChildren();

        display = win.innerWidth < 992 ? "mobile" : "desktop";

        group = new scope.Group();

        viewport = scope.view.center;
        group.position = scope.view.center;

        addChildren();

        drawing = false;
      };

      // recognize the mouse cordination
      var mouseCoordinates = function(points) {
        clearTimeout(mouse.onmove);
        mouse.x = points.x;
        mouse.y = points.y;

        if (true !== istouch) {
          mouseMove();
        }

        mouse.onmove = setTimeout(function() {
          mouse.onmove = false;
        }, 100);
      };

      // set limit radius for meshes
      var updateLimits = function(limit) {
        for (var i = 0, len = group.children.length; i < len; i++) {
          limit = (group.children[i].index + 1) / mouse.limit;
          group.children[i].limits = {
            x: {
              min: group.children[i].position.x - limit,
              max: group.children[i].position.x + limit
            },
            y: {
              min: group.children[i].position.y - limit,
              max: group.children[i].position.y + limit
            }
          };
        }

        // run animation
        scope.view.onFrame = true !== istouch ? tiltMove : null;
      };

      var shapes = {
        // generate a new triangle
        triangle: function(config, mesh) {
          mesh = new scope.Path.RegularPolygon(translate(config), 3, config[display].size);
          mesh.strokeColor = config.strokeColor;
          mesh.strokeWidth = config.strokeWidth;
          mesh.blendMode = config.blendMode || "normal";
          mesh.rotate(config.rotate || 0);
          group.addChild(mesh);
        },

        // generate a new circle
        circle: function(config, mesh) {
          mesh = new scope.Path.Circle(translate(config), config[display].size);
          mesh.strokeColor = config.strokeColor;
          mesh.strokeWidth = config.strokeWidth;
          mesh.blendMode = config.blendMode || "normal";
          group.addChild(mesh);
        },

        // generate a new wave path
        wave: function(config, mesh, size) {
          size = getCoordinates(config);
          size.a = config[display].size;
          size.b = Math.floor(size.a * 0.5);
          size.c = Math.floor(size.b * 0.5);

          mesh = new scope.Path();
          mesh.strokeColor = config.strokeColor;
          mesh.strokeWidth = config.strokeWidth;
          mesh.blendMode = config.blendMode || "normal";
          mesh.add(point(size.x - size.a, size.y));
          mesh.add(point(size.x - size.a, size.y));
          mesh.add(point(size.x - size.b, size.y + size.c));
          mesh.add(point(size.x, size.y));
          mesh.add(point(size.x + size.b, size.y + size.c));
          mesh.add(point(size.x + size.a, size.y));
          mesh.smooth({ type: "catmull-rom", factor: 0.5 });
          mesh.rotate(config.rotate || 0);
          group.addChild(mesh);
        },

        // generate a new raster
        raster: function(config, mesh) {
          mesh = new scope.Raster({
            source: config.src,
            position: translate(config)
          });
          mesh.blendMode = config.blendMode || "normal";
          mesh.on("load", function() {
            mesh.setHeight(mesh.height + 1);
            mesh.setHeight(mesh.height - 1); // fix issue https://github.com/paperjs/paper.js/issues/1192#issuecomment-300736753
            mesh.scale(config[display].scale || 0.5);
            mesh.rotate(config.rotate || 0);
          });
          group.addChild(mesh);
        }
      };

      var addChildren = function() {
        for (var i = 0, len = config.length; i < len; i++) {
          shapes[config[i].type] && shapes[config[i].type](config[i]);
        }

        updateLimits();
      };

      // strat drawing

      // add shapes
      update();

      // On resize
      var resizing = 0;
      scope.view.onResize = function(e) {
        scope.activate();
        scope.view._needsUpdate = true;
        scope.view.update();
        update();

        classie.add(parent, "resizing");
        clearTimeout(resizing);
        resizing = setTimeout(function() {
          classie.remove(parent, "resizing");
        }, 500);
      };

      // disable animations on window scroll event
      win.addEventListener(
        "scroll",
        function(e) {
          clearTimeout(pageScrolling);
          pageScrolling = setTimeout(function() {
            pageScrolling = false;
          }, 25);
        },
        false
      );

      // start mouse animation on mouse move event
      tools.onMouseMove = function(event) {
        mouseCoordinates(event.lastPoint);
      };
    });
  }

  /**
   * PaperJS patterns will give your site a colorful and playful look,
   * Users will enjoy to spend more time in the website.
   */
  function pixudio_gooey() {
    // paper has not included.
    if ("undefined" === typeof paper) return;
    // animate paper has not included.
    if ("undefined" === typeof animatePaper) return;

    doc.querySelectorAll(".paper--gooey").forEach(function(parent) {
      var canvas = parent.querySelector("canvas"),
        config = [].concat(win[parent.getAttribute("data-elements")]),
        scope = new paper.PaperScope();

      scope.setup(canvas);
      scope.view.viewSize.width = canvas.clientWidth;
      scope.view.viewSize.height = canvas.clientHeight;

      var tools = new scope.Tool(),
        drawing = false,
        pageScrolling = false,
        display = "desktop",
        mousePoint = new scope.Point(-1000, -1000),
        mouseForce = 0.15,
        shapes = [];

      // recognize display size & draw
      var update = function() {
        if (false !== drawing) {
          return;
        }

        drawing = true;

        scope.view.onFrame = null;
        scope.project.activeLayer.removeChildren();

        display = win.innerWidth < 992 ? "mobile" : "desktop";

        shapes = [];

        for (var i = 0, len = config.length; i < len; i++) {
          var shape = Object.assign({}, config[i]);
          var cords = {
            center: {
              x: scope.view.center.x + shape[display].center.x,
              y: scope.view.center.y + shape[display].center.y
            }
          };

          var mesh = Object.assign(
            {
              radius: 100,
              center: { x: 0, y: 0 },
              fillColor: "#00000"
            },
            shape[display],
            cords
          );

          shape.mesh = mesh;

          var mask = false;
          if ("mask" === shape.type) {
            mask = new scope.Raster({
              source: shape.src,
              position: mesh.center
            });
            mask.opacity = 0;
            mask.on("load", function() {
              animatePaper.animate(mask, {
                properties: {
                  opacity: 1
                },
                settings: {
                  duration: shape.fadeIn || 2000,
                  easing: "easeInOutCirc",
                  complete: function(item, animation) {}
                }
              });
            });
          }
          var circlePath = new scope.Path.Circle(mesh);
          if (shape.flatten) {
            circlePath.flatten(shape.flatten);
            circlePath.smooth({ type: "asymmetric" });
          }

          var rotationMultiplicator = mesh.radius / 200;
          var settings = [];
          for (var ii = 0; ii < circlePath.segments.length; ii++) {
            settings.push({
              relativeX: circlePath.segments[ii].point.x - mesh.center.x,
              relativeY: circlePath.segments[ii].point.y - mesh.center.y,
              offsetX: rotationMultiplicator,
              offsetY: rotationMultiplicator,
              momentum: new scope.Point(0, 0)
            });
          }

          shape.settings = settings;
          shape.threshold = mesh.radius * 1.4;
          shape.circlePath = circlePath;
          shape.group = new scope.Group([circlePath]);
          shape.controlCircle = circlePath.clone();
          shape.rotationMultiplicator = rotationMultiplicator;

          shape.controlCircle.fullySelected = false;
          shape.controlCircle.visible = false;

          if (mask !== false) {
            var maskGroup = new scope.Group([shape.group, mask]);
            // mask raster
            maskGroup.clipped = true;
            shape.mask = mask;
            shape.maskGroup = maskGroup;
          }

          circlePath.opacity = 0;
          animatePaper.animate(circlePath, {
            properties: {
              opacity: 1
            },
            settings: {
              duration: shape.fadeIn || 2000,
              easing: "easeInOutCirc",
              complete: function(item, animation) {}
            }
          });

          shapes.push(shape);
        }

        // run animation
        if (true !== istouch) {
          scope.view.onFrame = function(event) {
            animate(event);
          };
        }

        drawing = false;
      };

      // animation
      var animate = function(event) {
        for (var i = 0, len = shapes.length; i < len; i++) {
          var shape = shapes[i];
          var mesh = shape.mesh;
          shape.group.rotate(-0.2, mesh.center);
          for (var ii = 0; ii < shape.circlePath.segments.length; ii++) {
            var segment = shape.circlePath.segments[ii];

            var settings = shape.settings[ii];
            // var controlPoint = new scope.Point();
            var controlPoint = shape.controlCircle.segments[ii].point;

            // Avoid the mouse
            var mouseOffset = mousePoint.subtract(controlPoint);
            var mouseDistance = mousePoint.getDistance(controlPoint);
            var newDistance = 0;
            if (mouseDistance < shape.threshold) {
              newDistance = (mouseDistance - shape.threshold) * mouseForce;
            }

            var newOffset = new scope.Point(0, 0);
            if (mouseDistance !== 0) {
              newOffset = new scope.Point((mouseOffset.x / mouseDistance) * newDistance, (mouseOffset.y / mouseDistance) * newDistance);
            }

            var newPosition = controlPoint.add(newOffset);
            var distanceToNewPosition = segment.point.subtract(newPosition);

            settings.momentum = settings.momentum.subtract(distanceToNewPosition.divide(6));
            settings.momentum = settings.momentum.multiply(0.6);

            // Add automatic rotation
            var amountX = settings.offsetX;
            var amountY = settings.offsetY;
            var sinus = Math.sin(event.time + ii * 4);
            var cos = Math.cos(event.time + ii * 4);
            settings.momentum = settings.momentum.add(new scope.Point(cos * -amountX, sinus * -amountY));

            // go to the point, now!
            segment.point = segment.point.add(settings.momentum);
          }
        }
      };

      // strat drawing

      // add shapes
      update();

      // On resize
      scope.view.onResize = function(e) {
        scope.activate();
        scope.view._needsUpdate = true;
        scope.view.update();
        update();
      };

      // disable animations on window scroll event
      win.addEventListener(
        "scroll",
        function(e) {
          clearTimeout(self.pageScrolling);
          self.pageScrolling = setTimeout(function() {
            self.pageScrolling = false;
          }, 25);
        },
        false
      );

      // mouse move
      tools.onMouseMove = function(event) {
        mousePoint = event.lastPoint;
      };
    });
  }

  /**
   * PaperJS patterns will give your site a colorful and playful look,
   * Users will enjoy to spend more time in the website.
   */
  function pixudio_starts() {
    // paper has not included.
    if ("undefined" === typeof paper) return;

    doc.querySelectorAll(".paper--stars").forEach(function(parent) {
      var canvas = parent.querySelector("canvas"),
        config = win[parent.getAttribute("data-elements")],
        scope = new paper.PaperScope();

      scope.setup(canvas);
      scope.view.viewSize.width = canvas.clientWidth;
      scope.view.viewSize.height = canvas.clientHeight;

      var tools = new scope.Tool(),
        mousePos = new scope.Point(scope.view.center.x, scope.view.center.y + 100),
        position = scope.view.center;

      // strat drawing
      var build = function() {
        position = new scope.Point(position.x + (mousePos.x - position.x) / 10, position.y + (mousePos.y - position.y) / 10);
        var vector = new scope.Point((scope.view.center.x - position.x) / 10, (scope.view.center.y - position.y) / 10);
        moveStars(vector);
      };

      var moveStars = new function() {
        // The amount of symbol we want to place;
        var count = config.count || 50;

        // Create a symbol, which we will use to place instances of later:
        var path = new scope.Path.Circle({
          center: [0, 0],
          radius: config.radius || 4,
          fillColor: config.fillColor || "black"
        });

        var symbol = new scope.Symbol(path);

        // Place the instances of the symbol:
        for (var i = 0; i < count; i++) {
          // The center position is a random point in the view:
          var rand = scope.Point.random();
          var center = new scope.Point(rand.x * scope.view.size.width, rand.y * scope.view.size.height);
          var placed = symbol.place(center);
          placed.scale(i / count + 0.01);
          placed.data = {
            vector: new scope.Point({
              angle: Math.random() * 360,
              length: ((i / count) * Math.random()) / 5
            })
          };
        }

        var vector = new scope.Point({
          angle: 45,
          length: 0
        });

        function keepInView(item) {
          var position = item.position;
          var viewBounds = scope.view.bounds;
          if (position.isInside(viewBounds)) return;
          var itemBounds = item.bounds;
          if (position.x > viewBounds.width + 5) {
            position.x = -item.bounds.width;
          }

          if (position.x < -itemBounds.width - 5) {
            position.x = viewBounds.width;
          }

          if (position.y > viewBounds.height + 5) {
            position.y = -itemBounds.height;
          }

          if (position.y < -itemBounds.height - 5) {
            position.y = viewBounds.height;
          }
        }

        return function(vector) {
          // Run through the active layer's children list and change
          // the position of the placed symbols:
          var layer = scope.project.activeLayer;
          for (var i = 0; i < count; i++) {
            var item = layer.children[i];
            var size = item.bounds.size;
            var length = ((vector.length / 10) * size.width) / 10;
            // item.position += vector.normalize(length) + item.data.vector;
            var normalized = vector.normalize(length);
            item.position = new scope.Point(item.position.x + normalized.x + item.data.vector.x, item.position.y + normalized.y + item.data.vector.y);
            keepInView(item);
          }
        };
      }();

      // add shapes
      build();
      scope.view.onFrame = null;

      // run animation
      if (true !== istouch) {
        // mouse move
        tools.onMouseMove = function(event) {
          mousePos = event.lastPoint;
        };

        // animation
        scope.view.onFrame = build;
      }
    });
  }

  /**
   * This touch enabled plugin lets you create a beautiful responsive carousel slider.
   */
  function pixudio_carousel() {
    var carousel = doc.querySelectorAll(".carousel");

    // No carousel has found
    if (0 === carousel.length) return;

    // Siema has not included.
    if ("undefined" === typeof Siema) return;
    function generate(scope) {
      var self = false;
      var config = {
        selector: scope.querySelector(".carousel__frame"),
        duration: parseInt(scope.getAttribute("data-duration")) || 500,
        easing: scope.getAttribute("data-easing") || "ease",
        perPage: 1,
        draggable: true,
        threshold: 100,
        autoplay: parseInt(scope.getAttribute("data-autoplay")) || 3000,
        rotate: scope.getAttribute("data-rotate") || "on",
        onInit: init,
        onChange: update
      };

      //   console.log({ config });

      // handle carousel auto height
      function resize(first) {
        if (first === false) {
          self.selector.style.height = Math.ceil(self.innerElements[self.currentSlide].clientHeight) + "px";
        }
      }

      // auto play
      function next() {
        clearTimeout(self.autoPlayTimeout);
        self.autoPlayTimeout = setTimeout(function() {
          if (true === self.config.loop) {
            self.next();
          } else {
            if (self.currentSlide >= self.innerElements.length - 1) {
              self.goTo(self.config.startIndex);
              update("startIndex");
            } else {
              self.next();
            }
          }
        }, self.config.autoplay);
      }

      // handle carousel and its items classes
      function update(status) {
        self = self || this;
        var dashed = self.innerElements[self.currentSlide].querySelector(".dashed");

        if ("init" !== status && 0 < self.copies.length && 500 !== self.config.duration && true !== self.fistCopyDelaySet) {
          self.copies[0].style.animationDelay = self.config.duration + "ms";
          self.fistCopyDelaySet = true;
        }

        // recognise slide direction
        if (self.lastSlide > self.currentSlide) {
          classie.add(scope, "carousel--reverse");
        } else {
          classie.remove(scope, "carousel--reverse");
        }
        self.lastSlide = self.currentSlide;

        // remove all active classes
        for (var i = 0, len = self.innerElements.length; i < len; i++) {
          classie.remove(self.innerElements[i], "carousel__item--active");
          if (0 < self.dotElements.length) {
            classie.remove(self.dotElements[i], "active");
          }
          if (null !== dashed) {
            var dash = self.innerElements[i].querySelector(".dashed");
            if (dash !== null) {
              classie.remove(self.innerElements[i].querySelector(".dashed"), "in-view__child--in");
            }
          }
        }

        // add active class to current slide
        classie.add(self.innerElements[self.currentSlide], "carousel__item--active");
        if (0 < self.dotElements.length) {
          classie.add(self.dotElements[self.currentSlide], "active");
        }

        setTimeout(function() {
          if (null !== dashed) {
            classie.add(dashed, "in-view__child--in");
          }
        }, self.config.duration);

        // reset
        classie.remove(scope, "carousel--on-first");
        classie.remove(scope, "carousel--on-last");

        // if first item is active
        if (false === self.config.loop && 0 === self.currentSlide) {
          classie.add(scope, "carousel--on-first");
        }

        // if last item is active
        if (false === self.config.loop && self.innerElements.length - 1 === self.currentSlide) {
          classie.add(scope, "carousel--on-last");
        }

        // scope auto height
        resize(true);

        // autoplay
        if (self.config.rotate === "on") {
          next();
        }
      }

      // handle next, prev actions
      function init() {
        self = self || this;
        self.lastSlide = self.currentSlide;
        self.dotElements = [];
        self.dots = scope.querySelector(".carousel__dots");
        self.copies = scope.querySelectorAll(".carousel__copy");
        var prev = scope.querySelector(".carousel__prev");
        var next = scope.querySelector(".carousel__next");
        var emit = null;

        // go prev
        if (null !== prev) {
          prev.addEventListener("click", function() {
            self.prev();
          });
        }

        // go next
        if (null !== next) {
          next.addEventListener("click", function() {
            self.next();
          });
        }

        // set copies animation delay
        if (1 < self.copies.length && 500 !== self.config.duration) {
          for (var i = 1, len = self.copies.length - 1; i < len; i++) {
            self.copies[i].style.animationDelay = self.config.duration + "ms";
          }
        }

        // generate dots
        if (null !== self.dots && false === self.config.loop) {
          for (var i = 0, len = self.innerElements.length; i < len; i++) {
            var dot = doc.createElement("span");

            dot.slideTarget = i;

            if (i === self.currentSlide) {
              classie.add(dot, "active");
            }

            dot.style.transition = "all 0.6s " + Math.round((i * 0.1 + 0.2) * 10) / 10 + "s cubic-bezier(0.68, -1, 0.27, 2)";

            self.dotElements.push(dot);
            self.dots.appendChild(dot);

            dot.addEventListener("click", function() {
              self.goTo(this.slideTarget);
              update("dot");
            });
          }
        }

        // on window resize
        win.addEventListener(
          "resize",
          function() {
            classie.add(scope, "carousel--resizing");
            clearTimeout(emit);
            emit = setTimeout(function() {
              resize(false);
              classie.remove(scope, "carousel--resizing");
            }, 200);
          },
          false
        );

        // on carousel__item resize
        for (var i = 0, len = self.innerElements.length; i < len; i++) {
          self.innerElements[i].resizeSensor = new ResizeSensor(self.innerElements[i], function() {
            resize(false);
          });
        }

        update("init");

        classie.add(scope, "carousel--init");
      }

      scope.siema = new Siema(config);
    }
    // go
    for (var i = 0, len = carousel.length; i < len; i++) {
      generate(carousel[i]);
    }
  }

  /**
   * Scroll to, this plugin will trigger as soon as user clicks on a hashtag link
   * like href="#page", it looks up for that id in a same page and if its availbe
   * it scrolls the page to the id point, otherwise will ignore the action.
   * Home page navigation also uses this very same plugin, as one page websites,
   * that scrolled through eternity, with a sticky anchor link header at the top,
   * almost became the standard way of doing home pages.
   */
  function pixudio_scrollTo() {
    var anchors = doc.querySelectorAll('a[href^="#"]:not([href="#"])');

    // No inner page link has found
    if (0 === anchors.length) return;

    // animateScrollTo has not included.
    if ("undefined" === typeof animateScrollTo) return;

    for (var i = 0, len = anchors.length; i < len; i++) {
      anchors[i].addEventListener(
        "click",
        function(target, rect) {
          target = doc.querySelector(this.hash);

          // No target has found
          if (null === target) return;

          rect = target.getBoundingClientRect();

          // go
          animateScrollTo(rect.top + window.pageYOffset || 0, { cancelOnUserAction: false });
        },
        false
      );
    }
  }

  /**
   * Side menus, We are using this to display mobile menu, it also interact with
   * touch events as well, although you might use it for displaying widget or something else.
   */
  function pixudio_sideMenu() {
    // default options
    var self = {
      opened: false,
      trigger: doc.querySelectorAll(".side-menu-trigger"),
      swipeable: doc.querySelectorAll(".side-menu-swipeable"),
      sidemenu: doc.querySelector(".site-sidenav__elements"),
      overlay: doc.querySelector(".site-sidenav__overlay"),
      sidemenuitems: doc.querySelectorAll(".site-sidenav__elements a"),
      classes: {
        active: "side-menu",
        display: "side-menu--display",
        avoid: "side-menu-trigger"
      }
    };

    // No element has found.
    if (null === self.sidemenu) return;

    // display side-menu after 50ms
    function open() {
      if (false === self.opened) {
        classie.add(doc.documentElement, self.classes.active);
        setTimeout(function() {
          classie.add(doc.documentElement, self.classes.display);
          self.opened = true;
        }, 50);
      }
    }

    // hide side-menu after 300ms
    function close() {
      if (true === self.opened) {
        classie.remove(doc.documentElement, self.classes.display);
        setTimeout(function() {
          classie.remove(doc.documentElement, self.classes.active);
          self.opened = false;
        }, 300);
      }
    }

    // let’s user can close the menu with swipping
    function swipe() {
      // Hammer has not included.
      if ("undefined" === typeof Hammer) return;

      for (var i = 0, len = self.swipeable.length; i < len; i++) {
        var now = 0,
          max = self.sidemenu.clientWidth,
          handle = new Hammer(self.swipeable[i]);

        handle.on("panstart", function(e) {
          classie.add(doc.documentElement, "side-menu--panning");
        });

        // all out when swipe to the left
        handle.on("swipeleft", close);

        // check how much user has swipped
        handle.on("panright panleft", function(e) {
          now = now + (4 === e.direction ? Math.round(Math.max(3, e.velocity)) : Math.round(Math.min(-3, e.velocity)));

          if (now > 0) {
            now = 0;
          }

          if (Math.abs(now) > max) {
            now = max * -1;
          }

          self.overlay.style.opacity = 1 + (now * 1) / max;

          self.sidemenu.style.webkitTransform = "translateX(" + now + "px)";
          self.sidemenu.style.transform = "translateX(" + now + "px)";
        });

        // close / reset sidemenu status
        handle.on("panend pancancel", function(e) {
          classie.remove(doc.documentElement, "side-menu--panning");

          if (Math.abs(now) > max * 0.5) {
            close();
          }

          self.overlay.style.opacity = "";

          self.sidemenu.style.webkitTransform = "";
          self.sidemenu.style.transform = "";
          now = 0;
        });
      }
    }

    // activate swipe to close mode
    if (0 < self.swipeable.length) {
      swipe();
    }

    // close side-menu
    doc.addEventListener(
      "click",
      function(e) {
        if (true === self.opened && e.pageX > self.sidemenu.clientWidth && false === classie.has(e.target, self.classes.avoid)) {
          close();
        }
      },
      false
    );

    // close side-menu if user click on side-menu nav items
    if (null !== self.sidemenuitems && 0 < self.sidemenuitems.length) {
      for (var i = 0, len = self.sidemenuitems.length; i < len; i++) {
        self.sidemenuitems[i].addEventListener("click", close, false);
      }
    }

    // open side-menu
    if (null !== self.trigger && 0 < self.trigger.length) {
      for (var i = 0, len = self.trigger.length; i < len; i++) {
        self.trigger[i].addEventListener("click", open, false);
      }
    }
  }

  /**
   * Spot an element (scope) when it’s on users viewport,
   * After each scope is spotted, it will be check if it has include childrens -
   * those assigned to be specified by a class.
   */
  function pixudio_inView(scope) {
    scope = doc.getElementsByClassName("in-view");

    // No element has found.
    if (null === typeof scope || 0 === scope.length) return;

    // Waypoint has not included.
    if ("undefined" === typeof Waypoint) return;

    // default options
    // checkout @waypoints to find out how ”offset” is working http://imakewebthings.com/waypoints/api/offset-option/
    var options = {
      offset: "80%",
      delay: 200,
      classes: {
        child: "in-view__child",
        scope_in: "in-view--in",
        child_in: "in-view__child--in"
      }
    };

    // add class into elements
    function add(el, className, delay) {
      setTimeout(function() {
        classie.add(el, className);
      }, delay);
    }

    // attach waypoint into each scope
    for (var i = 0, len = scope.length; i < len; i++) {
      var waypoint = new Waypoint({
        element: scope[i],
        handler: function(direction) {
          var children = this.element.getElementsByClassName(options.classes.child);

          // check if this scope has any child that should specified as inview element
          if (0 < children.length) {
            for (var i = 0, len = children.length; i < len; i++) {
              add(children[i], options.classes.child_in, options.delay * (i + 1));
            }
          }

          // add class to the scope
          add(this.element, options.classes.scope_in, 0);

          // trigger inview only once
          this.destroy();
        },
        offset: scope[i].getAttribute("data-offset") || options.offset
      });
    }
  }

  /**
   * Fixed headers are a popular approach for keeping the primary navigation in
   * close proximity to the user. This can reduce the effort required for a user to
   * quickly navigate a site. @see http://wicky.nillia.ms/headroom.js/
   */
  function pixudio_stickyHeader(el, headroom) {
    el = doc.getElementById("masthead");

    // No element has found.
    if (null === el || null === typeof el || 0 === el.length) return;

    // Headroom has not included.
    if ("undefined" === typeof Headroom) return;

    // construct an instance of Headroom, passing the element
    headroom = new Headroom(el, {
      offset: el.clientHeight || 120
    });
    // initialise
    headroom.init();
  }

  /**
   * Easy access to the top of the page when user scrolls down more than viewport height.
   * quickly navigate a site. @see http://wicky.nillia.ms/headroom.js/
   */
  function pixudio_goUp(el, headroom) {
    el = doc.getElementById("up");

    // No element has found.
    if (null === el) return;

    // Headroom has not included.
    if ("undefined" === typeof Headroom) return;

    // construct an instance of Headroom, passing the element
    headroom = new Headroom(el, {
      offset: win.innerHeight
    });
    // initialise
    headroom.init();
  }

  /**
   * Tabs enable content organization at a high level, such as switching between views,
   * data sets, or functional aspects of a content.
   */
  function pixudio_tabs(tabs) {
    tabs = doc.querySelectorAll(".tabs");

    // No element has found.
    if (null === typeof tabs || 0 === tabs.length) return;

    function off(target, tab, elems, assignedTab) {
      if (true === classie.has(target, "tabs__nav--active")) {
        return;
      }

      assignedTab = tab.querySelector('.tabs__item[data-tab="' + target.getAttribute("data-tab") + '"]');

      if (null === assignedTab || 0 === assignedTab.length) {
        return;
      }

      for (var i = 0, len = elems.length; i < len; i++) {
        classie.remove(elems[i], "tabs__nav--active");
        classie.remove(elems[i], "tabs__item--active");
        elems[i].setAttribute("tabindex", "-1");
        elems[i].setAttribute("aria-selected", "false");
      }

      classie.add(target, "tabs__nav--active");
      target.setAttribute("tabindex", "0");
      target.setAttribute("aria-selected", "true");
      classie.add(assignedTab, "tabs__item--active");
      assignedTab.setAttribute("tabindex", "0");
      assignedTab.setAttribute("aria-selected", "true");
    }

    function apply(tab, nav, elems) {
      nav = tab.querySelectorAll(".tabs__nav");
      elems = tab.querySelectorAll("[data-tab]");

      for (var i = 0, len = nav.length; i < len; i++) {
        // add event listener
        nav[i].addEventListener(
          "click",
          function() {
            off(this, tab, elems);
          },
          false
        );
      }
    }

    for (var i = 0, len = tabs.length; i < len; i++) {
      apply(tabs[i]);
    }
  }

  /**
   * Instafeed is a dead-simple way to add Instagram photos to your website.
   */
  function pixudio_instafeed(feed) {
    // Instafeed has not included.
    if ("undefined" === typeof Instafeed) return;

    feed = doc.getElementById("instafeed");

    // No element has found.
    if (null === feed) return;

    function apply(feed, request, config, list) {
      config = feed.getAttribute("data-config");

      if (null === config || undefined === win[config] || undefined === win[config].userId || undefined === win[config].accessToken) return;

      request = new Instafeed({
        get: "user",
        userId: win[config].userId,
        accessToken: win[config].accessToken,
        limit: win[config].limit || 6,
        resolution: win[config].resolution || "standard_resolution",
        template: '<figure class="instagram-feed__item lazyload--el lazyload" data-bg="{{image}}"></figure>',
        error: function(e) {
          console.warn("Instagram feed warning:", e);
        },
        success: function(e) {
          // console.log('Data type could be one of "Image", "Video" or "Carousel"...', e.data);
        }
      });
      request.run();
    }

    apply(feed);
  }

  /**
   * Masonry works by placing elements in optimal position based on available vertical space,
   * sort of like a mason fitting stones in a wall.
   */
  function pixudio_masonry(grid) {
    grid = doc.querySelectorAll(".masonry");

    // No element has found.
    if (null === typeof grid || 0 === grid.length) return;

    // Masonry has not included.
    if ("undefined" === typeof Masonry) return;

    function laidOut(msnry) {
      setTimeout(function() {
        msnry.layout();
      }, 0);
    }

    for (var i = 0, len = grid.length; i < len; i++) {
      var msnry = new Masonry(grid[i], {
        // options
        itemSelector: ".masonry-item",
        // use element for option
        columnWidth: ".masonry-item",
        horizontalOrder: true,
        percentPosition: true
      });

      msnry.once("layoutComplete", function(items, counter, cols, options) {
        counter = 0;
        cols = items[0].layout.cols;

        // checkout @waypoints to find out how ”offset” is working http://imakewebthings.com/waypoints/api/offset-option/
        options = {
          offset: "80%",
          delay: 200,
          classes: {
            scope_in: "indexed-list__in-view--in"
          }
        };

        // add class into elements
        function add(el, className, delay) {
          setTimeout(function() {
            classie.add(el, className);
          }, delay);
        }

        // attach waypoint into each scope
        for (var i = 0, len = items.length; i < len; i++) {
          items[i].element.inViewDelay = counter * options.delay;

          counter++;

          if (counter === cols) counter = 0; // reset counter

          var waypoint = new Waypoint({
            element: items[i].element,
            handler: function(direction) {
              // add class to the scope
              add(this.element.querySelector(".indexed-list__in-view"), options.classes.scope_in, this.element.inViewDelay);

              // trigger inview only once
              this.destroy();
            },
            offset: options.offset
          });
        }
      });

      // go
      laidOut(msnry);
    }
  }

  /**
   * Mediabox is a essential way to offering embedded youtube and vimeo videos to users,
   * You can simply include it to any link, and lets users to decide what video they are
   * attempt to watch.
   */
  function pixudio_mediabox(popup) {
    popup = doc.querySelectorAll(".video-popup");

    // No element has found.
    if (null === typeof popup || 0 === popup.length) return;

    // MediaBox has not included.
    if ("undefined" === typeof MediaBox) return;

    // go
    MediaBox(".video-popup");
  }

  /**
   * Lazyload videos sources, this helps to increase site performance.
   */
  function pixudio_lazysource(video) {
    video = doc.querySelectorAll("[data-sources]");

    // No element has found.
    if (null === typeof video || 0 === video.length) return;

    function load(media, sources) {
      for (var i = 0, len = sources.length; i < len; i++) {
        var source = doc.createElement("source");
        media.appendChild(source);
        source.src = sources[i];
      }
      media.removeAttribute("data-sources");
      media.load();
    }

    // go
    for (var i = 0, len = video.length; i < len; i++) {
      try {
        var sources = video[i].getAttribute("data-sources").split("|");
        if (0 === sources.length) continue;
        load(video[i], sources);
      } catch (e) {
        console.warn(e);
      }
    }
  }

  /**
   * Fires when the initial HTML document has been completely loaded and parsed,
   * without waiting for stylesheets, images, and subframes to finish loading.
   */
  function pixudio_mailchimp(form, mcValidate) {
    form = doc.getElementById("mc-embedded-subscribe-form");

    // No element has found.
    if (null === form || null === typeof form || 0 === form.length) return;

    mcValidate = doc.createElement("script");
    mcValidate.type = "text/javascript";
    mcValidate.src = "https://s3.amazonaws.com/downloads.mailchimp.com/js/mc-validate.js";
    doc.head.appendChild(mcValidate);
    mcValidate.onload = function() {
      win["fnames"] = ["EMAIL", "FNAME"];
      win["ftypes"] = ["email", "text"];
      win["$mcj"] = jQuery.noConflict(true);
    };
  }

  /**
   * Countdown timers accentuate urgency. They almost make a game of it by dramatizing how little time is left to act.
   */
  function pixudio_countDownTimer(countdowns) {
    countdowns = doc.querySelectorAll(".countdown");

    // No element has found.
    if (null === typeof countdowns || 0 === countdowns.length) return;

    function count(cdt) {
      //
      var targetDate = cdt.getAttribute("data-count");
      if (undefined === targetDate) return;

      //
      var countDownDate = new Date(targetDate).getTime();
      if (true === isNaN(countDownDate) || true === isNaN(countDownDate - 0)) return;

      var recess;
      var output = [];
      var elms = cdt.querySelectorAll(".countdown__el");
      for (var i = 0, len = elms.length; i < len; i++) {
        var display = elms[i].getAttribute("data-display");
        if (undefined === display) continue;

        var displayCount = elms[i].querySelector(".countdown__count");
        if (null === displayCount) continue;

        var def = displayCount.innerText || "00";

        output.push({
          type: display,
          count: displayCount,
          default: def,
          length: def.length * -1,
          max: Array(def.length + 1).join("9") * 1
        });
      }

      function calc() {
        // Get todays date and time
        var now = new Date().getTime();
        // Find the distance between now an the count down date
        var distance = countDownDate - now;
        // If the count down is over, write some text
        if (distance < 0) {
          clearInterval(recess);
          console.warn("Countdown timer is expired!", { element: cdt, target: targetDate });
          return;
        }

        // Time calculations for days, hours, minutes and seconds
        var time = {
          days: Math.floor(distance / (1000 * 60 * 60 * 24)),
          hours: Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
          minutes: Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60)),
          seconds: Math.floor((distance % (1000 * 60)) / 1000)
        };

        for (var i = 0, len = output.length; i < len; i++) {
          var n = time[output[i].type];
          if (undefined === n) continue;

          output[i].count.innerText = n < output[i].max ? (output[i].default + n).slice(output[i].length) : n;
        }
      }

      // First run
      calc();

      // Update the count down every 1 second
      recess = setInterval(calc, 1000);
    }

    for (var i = 0, len = countdowns.length; i < len; i++) {
      count(countdowns[i]);
    }
  }

  /**
   * Google map
   */
  function pixudio_googleMap() {
    var maps = doc.querySelectorAll(".google-map");

    // No element has found.
    if (0 === maps.length) {
      return;
    }

    var styles = {
      silver: [
        {
          elementType: "geometry",
          stylers: [
            {
              color: "#efefef"
            }
          ]
        },
        {
          elementType: "labels.icon",
          stylers: [
            {
              visibility: "off"
            }
          ]
        },
        {
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#32353a"
            }
          ]
        },
        {
          elementType: "labels.text.stroke",
          stylers: [
            {
              color: "#f5f5f5"
            },
            {
              visibility: "off"
            }
          ]
        },
        {
          featureType: "administrative.land_parcel",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#bdbdbd"
            }
          ]
        },
        {
          featureType: "poi",
          elementType: "geometry",
          stylers: [
            {
              color: "#eeeeee"
            }
          ]
        },
        {
          featureType: "poi",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#757575"
            }
          ]
        },
        {
          featureType: "poi.park",
          elementType: "geometry",
          stylers: [
            {
              color: "#e5e5e5"
            }
          ]
        },
        {
          featureType: "poi.park",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#92959a"
            }
          ]
        },
        {
          featureType: "road",
          elementType: "geometry",
          stylers: [
            {
              color: "#ffffff"
            }
          ]
        },
        {
          featureType: "road.arterial",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#32353a"
            }
          ]
        },
        {
          featureType: "road.highway",
          elementType: "geometry",
          stylers: [
            {
              color: "#dadada"
            }
          ]
        },
        {
          featureType: "road.highway",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#616161"
            }
          ]
        },
        {
          featureType: "road.local",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#acb1bc"
            }
          ]
        },
        {
          featureType: "transit.line",
          elementType: "geometry",
          stylers: [
            {
              color: "#e5e5e5"
            }
          ]
        },
        {
          featureType: "transit.station",
          elementType: "geometry",
          stylers: [
            {
              color: "#eeeeee"
            }
          ]
        },
        {
          featureType: "water",
          elementType: "geometry",
          stylers: [
            {
              color: "#c9c9c9"
            }
          ]
        },
        {
          featureType: "water",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#9e9e9e"
            }
          ]
        }
      ],
      dark: [
        {
          elementType: "geometry",
          stylers: [
            {
              color: "#32353a"
            }
          ]
        },
        {
          elementType: "labels.icon",
          stylers: [
            {
              visibility: "off"
            }
          ]
        },
        {
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#72757a"
            }
          ]
        },
        {
          elementType: "labels.text.stroke",
          stylers: [
            {
              color: "#37393c"
            },
            {
              visibility: "off"
            }
          ]
        },
        {
          featureType: "administrative",
          elementType: "geometry",
          stylers: [
            {
              color: "#72757a"
            }
          ]
        },
        {
          featureType: "administrative.country",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#92959a"
            }
          ]
        },
        {
          featureType: "administrative.land_parcel",
          stylers: [
            {
              visibility: "off"
            }
          ]
        },
        {
          featureType: "administrative.locality",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#b2b5ba"
            }
          ]
        },
        {
          featureType: "poi",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#72757a"
            }
          ]
        },
        {
          featureType: "poi.park",
          elementType: "geometry",
          stylers: [
            {
              color: "#22252a"
            }
          ]
        },
        {
          featureType: "poi.park",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#62656a"
            }
          ]
        },
        {
          featureType: "poi.park",
          elementType: "labels.text.stroke",
          stylers: [
            {
              color: "#22252a"
            },
            {
              visibility: "off"
            }
          ]
        },
        {
          featureType: "road",
          elementType: "geometry.fill",
          stylers: [
            {
              color: "#2c2f35"
            }
          ]
        },
        {
          featureType: "road",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#82858a"
            }
          ]
        },
        {
          featureType: "road.arterial",
          elementType: "geometry",
          stylers: [
            {
              color: "#37393c"
            }
          ]
        },
        {
          featureType: "road.highway",
          elementType: "geometry",
          stylers: [
            {
              color: "#3c3c3c"
            }
          ]
        },
        {
          featureType: "road.highway.controlled_access",
          elementType: "geometry",
          stylers: [
            {
              color: "#4e4e4e"
            }
          ]
        },
        {
          featureType: "road.local",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#52555a"
            }
          ]
        },
        {
          featureType: "transit",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#75757a"
            }
          ]
        },
        {
          featureType: "water",
          elementType: "geometry",
          stylers: [
            {
              color: "#12151a"
            }
          ]
        },
        {
          featureType: "water",
          elementType: "labels.text.fill",
          stylers: [
            {
              color: "#32353a"
            }
          ]
        }
      ]
    };

    // Google map
    var initMap = function initMap() {
      var set = function set(canvas) {
        var theme = canvas.getAttribute("data-theme");
        var address = canvas.getAttribute("data-address");
        var zoom = canvas.getAttribute("data-zoom") || 15;
        var hasMarker = "false" !== canvas.getAttribute("data-marker");
        var scrollwheel = "true" === canvas.getAttribute("data-scrollwheel");
        var icon = JSON.parse(canvas.getAttribute("data-icon")) || { url: "assets/media/map-marker.svg", size: { width: 72, height: 72 } };
        var center = JSON.parse(canvas.getAttribute("data-location"));

        var draw = function draw() {
          var map = new google.maps.Map(canvas, {
            scrollwheel: scrollwheel,
            center: center,
            zoom: parseInt(zoom),
            styles: undefined !== styles[theme] ? styles[theme] : []
          });

          if (true === hasMarker) {
            new google.maps.Marker({
              map: map,
              animation: google.maps.Animation.DROP,
              position: center,
              draggable: false,
              optimized: false,
              icon: {
                url: icon.url,
                scaledSize: new google.maps.Size(icon.size.width, icon.size.height)
              }
            });
          }
        };

        if (null === center) {
          var geocoder = new google.maps.Geocoder();
          geocoder.geocode({ address: address }, function(results, status) {
            if (status == google.maps.GeocoderStatus.OK) {
              center = results[0].geometry.location;
              setTimeout(draw, 0);
            }
          });
        } else {
          setTimeout(draw, 0);
        }
      };

      // Setup an instance on each map
      maps.forEach(function(canvas) {
        return set(canvas);
      });
    };

    win.initMap = initMap;

    if ("undefined" === typeof google) {
      var script = doc.createElement("script");
      script.async = true;
      script.defer = true;
      script.src = "https://maps.googleapis.com/maps/api/js?key=" + maps[0].getAttribute("data-key") + "&callback=initMap";
      doc.head.appendChild(script);
    }
  }

  /**
   * Provide contextual feedback messages for typical user actions with
   * the handful of available and flexible alert messages.
   */
  function pixudio_alerts() {
    var alerts = doc.querySelectorAll(".alert .close");

    // No element has found.
    if (0 === alerts.length) return;

    alerts.forEach(function(alert) {
      return alert.addEventListener(
        "click",
        function() {
          return classie.add(alert.closest(".alert"), "sr-only");
        },
        false
      );
    });
  }

  /**
   * Toggle the visibility of content across your site
   */
  function pixudio_accordion() {
    var namespace = "accordion";
    var accordions = doc.querySelectorAll("." + namespace);

    // No accordion has found
    if (0 === accordions.length) return;

    var generate = function generate(scope) {
      var cards = scope.querySelectorAll("." + namespace + "__card");
      var headers = scope.querySelectorAll("." + namespace + "__header label");

      var toggle = function toggle(trigger) {
        var card = trigger.closest("." + namespace + "__card");
        var collapse = classie.has(card, namespace + "__card--collapse");

        // collapse all
        cards.forEach(function(card) {
          return classie.add(card, namespace + "__card--collapse");
        });

        if (true === collapse) {
          classie.remove(card, namespace + "__card--collapse");
        }
      };

      headers.forEach(function(header) {
        return header.addEventListener(
          "click",
          function() {
            return toggle(header);
          },
          false
        );
      });
    };

    accordions.forEach(function(scope) {
      return generate(scope);
    });
  }

  /**
   * Fires when the initial HTML document has been completely loaded and parsed,
   * without waiting for stylesheets, images, and subframes to finish loading.
   */
  function pixudio_init() {
    // add “is-touch” class to html tag if browser's touch APIs implemented,
    // whether or not the current device has a touchscreen.
    if (true === istouch) {
      classie.add(doc.documentElement, "is-touch");
    }

    // add “is-mac" class to html tag if OS is macintosh.
    if (true === isMac) {
      classie.add(doc.documentElement, "is-mac");
    }

    // add “is-chrome" class to html tag if browser is google chrome.
    if (true === isChrome) {
      classie.add(doc.documentElement, "is-chrome");
    }

    // Setup “paperJS”
    setTimeout(pixudio_paper, 0);

    // Setup “paperJS”
    setTimeout(pixudio_gooey, 0);

    // Setup “paperJS”
    setTimeout(pixudio_starts, 0);

    // Setup “carousel”
    setTimeout(pixudio_carousel, 0);

    // Setup “scroll to”
    setTimeout(pixudio_scrollTo, 0);

    // Setup “side menu”
    setTimeout(pixudio_sideMenu, 0);

    // Setup “sticky header”
    setTimeout(pixudio_stickyHeader, 0);

    // Setup “go up”
    setTimeout(pixudio_goUp, 0);

    // Setup “tabs”
    setTimeout(pixudio_tabs, 0);

    // Setup "masonry"
    setTimeout(pixudio_masonry, 0);

    // Setup "mediabox"
    setTimeout(pixudio_mediabox, 0);

    // Setup "mailchimp"
    setTimeout(pixudio_mailchimp, 0);

    // Setup “instagram feed”
    setTimeout(pixudio_instafeed, 0);

    // Setup “in view”
    setTimeout(pixudio_inView, 0);

    // Setup "countdown timer"
    setTimeout(pixudio_countDownTimer, 0);

    // Setup "google map"
    setTimeout(pixudio_googleMap, 0);

    // Setup "alert"
    setTimeout(pixudio_alerts, 0);

    // Setup "accordion"
    setTimeout(pixudio_accordion, 0);

    // Setup "lazy source"
    setTimeout(pixudio_lazysource, 0);
  }

  /**
   * Fires when a resource and its dependent resources have finished loading.
   */
  function pixudio_onload() {
    // add “loaded” class to html tag,
    classie.add(doc.documentElement, "loaded");
  }
  win.addEventListener("load", pixudio_onload);

  // trigger on document.ready scripts
  pixudio_init();
})(document, window);
