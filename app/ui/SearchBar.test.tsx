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

  test('Should call addProductToList when a suggestion is clicked and confirmed', async () => {
    mockedSearchProducts.mockResolvedValue([
      { id: 1, name: 'Mleko' },
    ]);

    render(<SearchBar />);
    
    const input = screen.getByPlaceholderText(/Szukaj lub dodaj produkt/i);
    await userEvent.type(input, 'ml');

    const suggestion = await screen.findByText('Mleko');
    await userEvent.click(suggestion);

    // Should show quantity modal and NOT call action yet
    expect(screen.getByText(/Ile sztuk:/i)).toBeInTheDocument();
    expect(screen.getAllByText('Mleko').length).toBeGreaterThan(0);
    expect(mockedAddProductToList).not.toHaveBeenCalled();

    const addButton = screen.getByRole('button', { name: /Dodaj/i });
    await userEvent.click(addButton);

    expect(mockedAddProductToList).toHaveBeenCalledWith(1, '1');
    await waitFor(() => expect(input).toHaveValue(''));
  });

  test('Should allow custom quantity and call addProductToList', async () => {
    mockedSearchProducts.mockResolvedValue([
      { id: 1, name: 'Mleko' },
    ]);

    render(<SearchBar />);
    
    const input = screen.getByPlaceholderText(/Szukaj lub dodaj produkt/i);
    await userEvent.type(input, 'ml');

    const suggestion = await screen.findByText('Mleko');
    await userEvent.click(suggestion);

    const quantityInput = screen.getByPlaceholderText(/Ilość/i);
    await userEvent.clear(quantityInput);
    await userEvent.type(quantityInput, '2 litry');

    const addButton = screen.getByRole('button', { name: /Dodaj/i });
    await userEvent.click(addButton);

    expect(mockedAddProductToList).toHaveBeenCalledWith(1, '2 litry');
  });

  test('Should navigate suggestions with keyboard and open quantity modal', async () => {
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

    // Should show quantity modal for Masło
    expect(screen.getByText(/Ile sztuk:/i)).toBeInTheDocument();
    expect(screen.getAllByText('Masło').length).toBeGreaterThan(0);
    expect(mockedAddProductToList).not.toHaveBeenCalled();

    // Enter again to confirm default quantity
    fireEvent.keyDown(screen.getByPlaceholderText(/Ilość/i), { key: 'Enter' });

    expect(mockedAddProductToList).toHaveBeenCalledWith(2, '1');
    await waitFor(() => expect(input).toHaveValue(''));
  });
});
