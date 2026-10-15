import SwiftUI

enum Calc {
    static func mul(_ a: Int, _ b: Int) -> Int { a * b }
}

@main
struct AcciDemoApp: App {
    var body: some Scene {
        WindowGroup {
            Text("ACCI Demo: 6 × 7 = \(Calc.mul(6, 7))")
                .font(.title)
                .padding()
        }
    }
}
