(function () {
    var specs = {'com.github.catsout.wallpaperEngineKde': ['SteamLibraryPath', 'WallpaperWorkShopId', 'WallpaperSource'],
                 'org.kde.image': ['Image', 'PreviewImage']};
    var activity = currentActivity();
    var result = {schema: 2, activity: activity, targets: []};
    desktopsForActivity(activity).filter(function (d) { return d.screen >= 0; }).forEach(function (d) {
        var target = {containment: d.id, screen: d.screen, plugin: d.wallpaperPlugin,
                      geometry: screenGeometry(d.screen), groups: {}};
        var group = d.currentConfigGroup;
        try {
            Object.keys(specs).forEach(function (plugin) {
                d.currentConfigGroup = ['Wallpaper', plugin, 'General'];
                target.groups[plugin] = {};
                specs[plugin].forEach(function (key) {
                    var present = d.configKeys.indexOf(key) !== -1;
                    var value = present ? d.readConfig(key) : null;
                    // Normalize: '' after writeConfig(key,'') is semantically absent in KConfig.
                    if (present && value === '') { present = false; value = null; }
                    target.groups[plugin][key] = {present: present, value: value};
                });
            });
        } finally { d.currentConfigGroup = group; }
        var g = target.geometry;
        target.geometry = {x: g.x, y: g.y, width: g.width, height: g.height};
        result.targets.push(target);
    });
    print(JSON.stringify(result));
})();
