/** @jest-environment jsdom */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SearchBar from './SearchBar';
import { searchProducts, addProductToList } from '@/app/actions/shopping-list';

// Mock server actions
jest.mock('@/app/actions/shopping-list', () => ({
  searchProducts: jest.fn(),
  addProductToList: jest.fn(),
}));

const mockedSearchProducts = searchProducts as jest.Mock;
const mockedAddProductToList = addProductToList as jest.Mock;

describe('SearchBar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('Should show suggestions when typing', async () => {
    mockedSearchProducts.mockResolvedValue([
      { id: 1, name: 'Mleko' },
      { id: 2, name: 'Masło' },
    ]);

    render(<SearchBar />);
    
    const input = screen.getByPlaceholderText(/Szukaj lub dodaj produkt/i);
    await userEvent.type(input, 'ml');

    await waitFor(() => {
      expect(screen.getByText('Mleko')).toBeInTheDocument();
      expect(screen.getByText('Masło')).toBeInTheDocument();
    });
  });

  test('Should call addProductToList when a suggestion is clicked', async () => {
    mockedSearchProducts.mockResolvedValue([
      { id: 1, name: 'Mleko' },
    ]);

    render(<SearchBar />);
    
    const input = screen.getByPlaceholderText(/Szukaj lub dodaj produkt/i);
    await userEvent.type(input, 'ml');

    const suggestion = await screen.findByText('Mleko');
    await userEvent.click(suggestion);

    expect(mockedAddProductToList).toHaveBeenCalledWith(1);
    await waitFor(() => expect(input).toHaveValue(''));
  });

  test('Should navigate suggestions with keyboard', async () => {
     mockedSearchProducts.mockResolvedValue([
      { id: 1, name: 'Mleko' },
      { id: 2, name: 'Masło' },
    ]);

    render(<SearchBar />);
    
    const input = screen.getByPlaceholderText(/Szukaj lub dodaj produkt/i);
    await userEvent.type(input, 'ml');

    // Wait for suggestions
    await screen.findByText('Mleko');

    // Arrow down to Mleko
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    // Arrow down to Masło
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    // Enter to select Masło
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockedAddProductToList).toHaveBeenCalledWith(2);
    await waitFor(() => expect(input).toHaveValue(''));
  });
});
