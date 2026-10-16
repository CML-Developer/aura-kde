pub fn is_pure_cli(args: &[String]) -> bool {
    args.get(1)
        .is_some_and(|s| !matches!(s.as_str(), "switcher" | "--hidden"))
}
pub fn handle_pure_cli(args: &[String]) {
    if args.get(1).is_some_and(|s| s == "--kde-info") {
        println!("aura-kde-lab: KDE adapter, both screens");
        return;
    }
    eprintln!("Aura KDE: open without arguments for the Workshop library, or use 'switcher'. Unsupported command: {:?}", args.get(1));
}
pub fn parse_flags(args: &[String]) -> (bool, Option<String>, Vec<String>) {
    let switcher = args.iter().any(|s| s == "switcher");
    (
        switcher || args.iter().any(|s| s == "--hidden"),
        switcher.then(|| "switcher".into()),
        Vec::new(),
    )
}
