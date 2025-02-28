import React, { useState } from 'react';
import { Button, Box, Text } from '@chakra-ui/react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';

export const WalletConnection: React.FC = () => {
    const { 
        publicKey, 
        wallet, 
        connected, 
        disconnect 
    } = useWallet();

    const [error, setError] = useState<string | null>(null);

    const handleDisconnect = async () => {
        try {
            await disconnect();
        } catch (err: unknown) {
            setError('Failed to disconnect wallet');
            console.error('Wallet disconnection error:', err);
        }
    };

    return (
        <Box display="flex" alignItems="center" gap={4}>
            {error && (
                <Text color="red.500" mr={4}>
                    {error}
                </Text>
            )}

            {connected && publicKey ? (
                <Box display="flex" alignItems="center" gap={4}>
                    <Text>
                        Connected: {publicKey.toBase58().slice(0, 6)}...{publicKey.toBase58().slice(-6)}
                    </Text>
                    <Button 
                        colorScheme="red" 
                        size="sm" 
                        onClick={handleDisconnect}
                    >
                        Disconnect
                    </Button>
                </Box>
            ) : (
                <WalletMultiButton />
            )}
        </Box>
    );
};