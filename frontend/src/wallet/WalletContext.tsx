import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { 
    ConnectionProvider, 
    WalletProvider as SolanaWalletProvider, 
    useConnection, 
    useWallet as useSolanaWallet
} from '@solana/wallet-adapter-react';
import { 
    WalletAdapterNetwork, 
    WalletError 
} from '@solana/wallet-adapter-base';
import { 
    PhantomWalletAdapter 
} from '@solana/wallet-adapter-wallets';
import { WalletModalProvider } from '@solana/wallet-adapter-react-ui';
import axios from 'axios';
import { PublicKey } from '@solana/web3.js';

// Import styles for wallet modal
import '@solana/wallet-adapter-react-ui/styles.css';

interface WalletContextType {
    isConnected: boolean;
    publicKey: PublicKey | null;
    walletAddress: string | null;
    balance: number | null;
    connect: () => Promise<void>;
    disconnect: () => Promise<void>;
    signTransaction: (transaction: any) => Promise<{ signature: string; signedTransaction: any }>;
    error: string | null;
    isInitialized: boolean;
    importPrivateKey: (privateKey: string) => Promise<void>;
    phantomWallets: string[];
    importedWallets: string[];
    maxImportedWallets: number;
    isImportedWallet: boolean;
}

const WalletContext = createContext<WalletContextType | undefined>(undefined);

interface WalletProviderProps {
    children: ReactNode;
}

export const WalletProvider: React.FC<WalletProviderProps> = ({ children }) => {
    const [isInitialized, setIsInitialized] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [phantomWallets, setPhantomWallets] = useState<string[]>([]);
    const [importedWallets, setImportedWallets] = useState<string[]>([]);
    const [maxImportedWallets, setMaxImportedWallets] = useState(20);
    const [isImportedWallet, setIsImportedWallet] = useState(false);

    // Solana Wallet Adapter hooks
    const { 
        publicKey, 
        wallet, 
        connected, 
        connect: solanaConnect, 
        disconnect: solanaDisconnect 
    } = useSolanaWallet();
    const { connection } = useConnection();

    const apiClient = axios.create({
        baseURL: import.meta.env.VITE_BACKEND_URL || '/api',
        withCredentials: false, // Changed from true to false to avoid CORS issues
        timeout: 30000 // Increased timeout to 30 seconds
    });

    const fetchWalletList = useCallback(async () => {
        try {
            const response = await apiClient.get('/soleco/wallet/list', {
                timeout: 60000, // 60 second timeout
                // Don't throw errors for 404 responses since the wallet service might not be available
                validateStatus: (status) => (status >= 200 && status < 300) || status === 404
            });
            
            if (response.status === 404) {
                console.log('Wallet service not available, using default values');
                setPhantomWallets([]);
                setImportedWallets([]);
                setMaxImportedWallets(10);
                return;
            }
            
            const { phantom_wallets, imported_wallets, max_imported_wallets } = response.data;
            setPhantomWallets(phantom_wallets || []);
            setImportedWallets(imported_wallets || []);
            setMaxImportedWallets(max_imported_wallets || 10);
        } catch (err) {
            console.error('Failed to fetch wallet list', err);
            // Don't show error to user, just use default values
            setPhantomWallets([]);
            setImportedWallets([]);
            setMaxImportedWallets(10);
        }
    }, []);

    const connect = useCallback(async () => {
        try {
            await solanaConnect();
            
            if (publicKey) {
                // Notify backend about connection
                await apiClient.post('/soleco/wallet/connect', {
                    public_key: publicKey.toBase58()
                });

                // Fetch wallet balance
                const balanceResponse = await apiClient.get(`/soleco/wallet/balance/${publicKey.toBase58()}`);
                setIsImportedWallet(false);
            }
        } catch (err) {
            console.error('Connection failed', err);
            setError('Failed to connect wallet');
        }
    }, [publicKey, solanaConnect]);

    const disconnect = useCallback(async () => {
        try {
            await solanaDisconnect();
            
            // Notify backend about disconnection
            if (publicKey) {
                await apiClient.post('/soleco/wallet/disconnect', {
                    public_key: publicKey.toBase58()
                });
            }
        } catch (err) {
            console.error('Disconnection failed', err);
            setError('Failed to disconnect wallet');
        }
    }, [publicKey, solanaDisconnect]);

    const importPrivateKey = useCallback(async (privateKey: string) => {
        try {
            const response = await apiClient.post('/soleco/wallet/import', { private_key: privateKey });
            const importedWallet = response.data.public_key;
            
            // Update imported wallets list
            setImportedWallets(prev => [...prev, importedWallet]);
            setIsImportedWallet(true);
        } catch (err) {
            console.error('Private key import failed', err);
            setError('Failed to import wallet');
        }
    }, []);

    const signTransaction = useCallback(async (transaction: any) => {
        if (!publicKey || !wallet) {
            throw new Error('Wallet not connected');
        }

        try {
            const signedTransaction = await wallet.adapter.signTransaction(transaction);
            
            // Optional: Send signature to backend for verification
            const signature = await apiClient.post('/soleco/wallet/sign-transaction', { 
                transaction: signedTransaction, 
                public_key: publicKey.toBase58() 
            });
            
            return { 
                signature: signature.data.signature, 
                signedTransaction 
            };
        } catch (err) {
            console.error('Transaction signing failed', err);
            throw new Error('Failed to sign transaction');
        }
    }, [publicKey, wallet]);

    useEffect(() => {
        fetchWalletList();
    }, [fetchWalletList]);

    useEffect(() => {
        setIsInitialized(true);
    }, []);

    const contextValue: WalletContextType = {
        isConnected: connected,
        publicKey,
        walletAddress: publicKey ? publicKey.toBase58() : null,
        balance: null, // TODO: Implement balance retrieval
        connect,
        disconnect,
        signTransaction,
        error,
        isInitialized,
        importPrivateKey,
        phantomWallets,
        importedWallets,
        maxImportedWallets,
        isImportedWallet
    };

    return (
        <WalletContext.Provider value={contextValue}>
            {children}
        </WalletContext.Provider>
    );
};

// Wrapper component to provide Solana Wallet context
export const SolanaWalletContextProvider: React.FC<WalletProviderProps> = ({ children }) => {
    // Can be set to 'devnet', 'testnet', or 'mainnet-beta'
    const network = WalletAdapterNetwork.Mainnet;

    // You can also provide a custom RPC endpoint
    const endpoint = import.meta.env.VITE_SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com';

    // @solana/wallet-adapter-wallets includes all the adapters but supports tree shaking
    const wallets = [
        new PhantomWalletAdapter()
    ];

    return (
        <ConnectionProvider endpoint={endpoint}>
            <SolanaWalletProvider 
                wallets={wallets} 
                autoConnect
                onError={(error: WalletError) => {
                    console.error('Wallet connection error:', error);
                }}
            >
                <WalletModalProvider>
                    <WalletProvider>
                        {children}
                    </WalletProvider>
                </WalletModalProvider>
            </SolanaWalletProvider>
        </ConnectionProvider>
    );
};

export const useWallet = (): WalletContextType => {
    const context = useContext(WalletContext);
    if (context === undefined) {
        throw new Error('useWallet must be used within a WalletProvider');
    }
    return context;
};

export const useWalletBalance = () => {
    const { balance, isConnected } = useWallet();
    return { balance, isConnected };
};

export const useWalletConnection = () => {
    const { isConnected, connect, disconnect, error } = useWallet();
    return { isConnected, connect, disconnect, error };
};