import "./globals.css";import AppChrome from "../components/AppChrome";
export const metadata={title:"VTAB AI Sales Intelligence",description:"AI-powered global opportunity discovery, qualification and sales intelligence platform."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><AppChrome>{children}</AppChrome></body></html>}
